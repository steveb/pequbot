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
import jsonschema
import requests
import yaml

import json
import os
import sys

SCHEMA = {
    'type': 'object',
    'properties': {
        'sources': {
            'type': 'object'
        },
        'queries': {
            'type': 'object'
        }
    }
}

SOURCE_SCHEMA = {
    'type': 'object',
    'required': ['url'],
    'properties': {
        'url': {'type': 'string'},
        'params': {
            'type': 'object',
            'properties': {
                'url': {'type': 'object'},
                'query': {'type': 'object'}
            }
        },
        'response_prefix': {'type': 'string'}
    }
}

QUERY_SCHEMA = {
    'type': 'object',
    'required': ['period_seconds', 'channel', 'source', 'params', 'template'],
    'properties': {
        'period_seconds': {'type': 'integer'},
        'channel': {'type': 'string'},
        'source': {'type': 'string'},
        'params': {'type': 'object'},
        'template': {'type': 'string'}
    }
}


class Result(object):

    def __init__(self, channel, message, url):
        self.channel = channel
        self.message = message
        self.url = url


class Caller(object):

    def __init__(self, channel_config):
        jsonschema.validate(channel_config, SCHEMA)
        self.sources = channel_config.get('sources', {})
        for s in self.sources.values():
            jsonschema.validate(s, SOURCE_SCHEMA)

        self.queries = channel_config.get('queries', {})
        self.channels = set()
        for q in self.queries.values():
            jsonschema.validate(q, QUERY_SCHEMA)
            if q['source'] not in self.sources:
                raise Exception('source %s missing from sources %s' %
                                (q['source'], self.sources.keys()))
            self.channels.add('#' + q['channel'])

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

    def call(self, query):
        source = self.sources[query['source']]

        url, params = self.build_api_url(source, query)
        headers = {'Content-Type': 'application/json'}
        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()

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

        return Result(channel, message, r.url)

    def call_all(self):
        for query in self.queries.values():
            yield self.call(query)


def main():
    if len(sys.argv) != 2:
        print("Usage: %s CHANNEL_YAML_FILE" % sys.argv[0])
        sys.exit(1)

    fp = os.path.expanduser(sys.argv[1])
    if not os.path.exists(fp):
        raise Exception("Unable to read layout config file at %s" % fp)

    channel_config = yaml.safe_load(open(fp))

    caller = Caller(channel_config)
    for result in caller.call_all():
        print('===')
        print(result.channel)
        print(result.url)
        print(result.message)


if __name__ == "__main__":
    main()
