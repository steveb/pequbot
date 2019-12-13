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

import configparser
import functools
from ib3.auth import SASL
from ib3.connection import SSL
import irc.bot
import logging.config
import os
import sys
import time
import yaml

from pequbot import query

# The configuration file should look like:
"""
[main]
nick=NICKNAME
pass=PASSWORD
server=irc.freenode.net
port=6697
channel_config=/path/to/yaml/config
"""

# The yaml channel config should look like:
"""
"""

# Freenode only allows a connection to join up to 120 channels
CHANNEL_MAX = 120


class Channel(object):
    def __init__(self, name):
        self.name = name
        self.stamp()

    def stamp(self):
        self.last_used = time.time()


class Pequbot(SASL, SSL, irc.bot.SingleServerIRCBot):
    def __init__(self, caller, nickname, password, server, port=6697):
        super(Pequbot, self).__init__(
            server_list=[(server, port)],
            nickname=nickname,
            realname=nickname,
            ident_password=password)
        self.all_channels = {}
        for name in caller.channels:
            self.all_channels[name] = Channel(name)
        self.joined_channels = {}
        self.nickname = nickname
        self.password = password
        self.log = logging.getLogger('pequbot')
        self.caller = caller

        for name, q in caller.queries.items():
            call_query = functools.partial(self.call_query, name)
            period = q['period_seconds']
            self.log.info('Running %s every %s seconds' % (name, period))
            self.reactor.scheduler.execute_after(30, call_query)
            self.reactor.scheduler.execute_every(period, call_query)

    def call_query(self, query_name):
        self.log.info('Running query %s' % query_name)
        query = self.caller.queries[query_name]
        result = self.caller.call(query)
        for message in result.message.split("\n"):
            self.send(result.channel, message)

    def send(self, channel_name, msg):
        self.log.info('Sending "%s" to %s' % (msg, channel_name))
        if channel_name not in self.joined_channels:
            if len(self.joined_channels) >= CHANNEL_MAX:
                drop = sorted(self.joined_channels.values(),
                              key=lambda x: x.last_used)[-1]
                self.connection.part(drop.name)
                self.log.info('Parted channel %s' % drop.name)
                del self.joined_channels[drop.name]
            channel = self.all_channels[channel_name]
            self.connection.join(channel.name)
            self.joined_channels[channel.name] = channel
            self.log.info('Joined channel %s' % channel.name)
            time.sleep(0.5)
        self.all_channels[channel_name].stamp()
        try:
            self.connection.privmsg(channel_name, msg)
            time.sleep(0.5)
        except Exception:
            self.log.exception('Exception sending message:')
            self.connection.reconnect()


def _main(config):
    setup_logging(config)

    fp = config.get('main', 'channel_config')
    if fp:
        fp = os.path.expanduser(fp)
        if not os.path.exists(fp):
            raise Exception("Unable to read layout config file at %s" % fp)
    else:
        raise Exception("Channel Config must be specified in config file.")

    try:
        channel_config = yaml.safe_load(open(fp))
        caller = query.Caller(channel_config)
    except Exception:
        log = logging.getLogger('gerritbot')
        log.exception("Syntax error in chanel config file")
        raise

    bot = Pequbot(caller,
                  config.get('main', 'nick'),
                  config.get('main', 'pass'),
                  config.get('main', 'server'),
                  config.getint('main', 'port'))
    bot.start()


def main():
    if len(sys.argv) != 2:
        print("Usage: %s CONFIGFILE" % sys.argv[0])
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(sys.argv[1])

    # pid_path = ""
    # if config.has_option('main', 'pid'):
    #     pid_path = config.get('main', 'pid')
    # else:
    #     pid_path = "/var/run/gerritbot/gerritbot.pid"

    # pid = pid_file_module.TimeoutPIDLockFile(pid_path, 10)
    # with daemon.DaemonContext(pidfile=pid):
    _main(config)


def setup_logging(config):
    if config.has_option('main', 'log_config'):
        log_config = config.get('main', 'log_config')
        fp = os.path.expanduser(log_config)
        if not os.path.exists(fp):
            raise Exception("Unable to read logging config file at %s" % fp)
        logging.config.fileConfig(fp)
    else:
        logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    main()
