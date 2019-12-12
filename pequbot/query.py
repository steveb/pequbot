#! /usr/bin/env python
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import jinja2
import requests
import yaml

import json
import os
import sys

# The yaml channel config should look like:
"""
"""


class QueryResult(object):

    def __init__(self, channel, message, url):
        self.channel = channel
        self.message = message
        self.url = url


class Query(object):

    def __init__(self, sources, queries, sender_func):
        self.sources = sources
        self.queries = queries
        self.sender_func = sender_func

    def build_api_url(self, source, query):
        url = source['url']
        source_params = source.get('params', {})
        qs_params = dict(source_params.get('query', {}))
        url_params = dict(source_params.get('url', {}))

        param_values = dict(query.get('params', {}))

        for k, v in param_values.items():
            if k in qs_params:
                qs_params[k] = v
            if k in url_params:
                url_params[k] = v

        if url_params:
            template = jinja2.Template(url)
            url = template.render(url_params)

        return url, qs_params

    def query(self, query):
        source = self.sources[query['source']]

        url, params = self.build_api_url(source, query)
        headers = {'Content-Type': 'application/json'}
        r = requests.get(url, params=params, headers=headers)

        channel = '#' + query['channel']

        template = jinja2.Template(query['template'])
        if 'response_prefix' in source:
            prefix = source['response_prefix']
            result_text = r.text
            if r.text.startswith(prefix):
                result_text = result_text[len(prefix):]
            result = json.loads(result_text)

        else:
            result = r.json()
        message = template.render(result=result)

        self.sender_func(QueryResult(channel, message, r.url))

    def query_all(self):
        for name in self.queries:
            query = self.queries[name]
            self.query(query)


def main():
    if len(sys.argv) != 2:
        print("Usage: %s CHANNEL_YAML_FILE" % sys.argv[0])
        sys.exit(1)

    fp = os.path.expanduser(sys.argv[1])
    if not os.path.exists(fp):
        raise Exception("Unable to read layout config file at %s" % fp)

    channel_config = yaml.safe_load(open(fp))

    def sender_print(result):
        print('===')
        print(result.channel)
        print(result.url)
        print(result.message)

    query = Query(
        channel_config.get('sources', {}),
        channel_config.get('queries', {}),
        sender_print
    )
    query.query_all()



if __name__ == "__main__":
    main()
