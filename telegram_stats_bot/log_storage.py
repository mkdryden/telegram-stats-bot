# !/usr/bin/env python
#
# A logging and statistics bot for Telegram based on python-telegram-bot.
# Copyright (C) 2020
# Michael DM Dryden <mk.dryden@utoronto.ca>
#
# This file is part of telegram-stats-bot.
#
# telegram-stats-bot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Public License
# along with this program. If not, see [http://www.gnu.org/licenses/].
from copy import copy

import datetime
import logging
import json
import os

from sqlalchemy import MetaData, Table, Column, create_engine, BigInteger, TIMESTAMP, Text
from sqlalchemy_utils import database_exists
from sqlalchemy_utils.functions.orm import quote

from .parse import MessageDict
from .db import init_dbs

logger = logging.getLogger(__name__)
metadata = MetaData()

messages = Table('messages_utc', metadata,
                 Column('message_id', BigInteger),
                 Column('date', TIMESTAMP),
                 Column('from_user', BigInteger),
                 Column('forward_from_message_id', BigInteger),
                 Column('forward_from', BigInteger),
                 Column('forward_from_chat', BigInteger),
                 Column('caption', Text),
                 Column('text', Text),
                 Column('sticker_set_name', Text),
                 Column('new_chat_title', Text),
                 Column('reply_to_message', BigInteger),
                 Column('file_id', Text),
                 Column('type', Text))
user_events = Table('user_events', metadata,
                    Column('message_id', BigInteger),
                    Column('user_id', BigInteger),
                    Column('date', TIMESTAMP),
                    Column('event', Text))


def date_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


class JSONStore(object):
    def __init__(self, path: str):
        self.store = path

    def append_data(self, name: str, data: MessageDict):
        with open(os.path.join(self.store, f"{name}.json"), 'a') as f:
            f.write(json.dumps(data, default=date_converter) + "\n")


class PostgresStore(object):
    def __init__(self, connection_url: str):
        self.engine = create_engine(connection_url, echo=False, isolation_level="AUTOCOMMIT")
        if not database_exists(self.engine.url):
            text = f"""
                    CREATE DATABASE {quote(self.engine, self.engine.url.database)}
                    ENCODING 'utf-8'
                    TEMPLATE {quote(self.engine, 'template1')}
                    """

            url = self.engine.url.set(database='postgres')

            engine = create_engine(url, echo=False, isolation_level="AUTOCOMMIT")
            result_proxy = engine.execute(text)

            if result_proxy is not None:
                result_proxy.close()
            engine.dispose()

        init_dbs(self.engine)

    def append_data(self, name: str, data: MessageDict):
        data['date'] = str(data['date'])
        if name == 'messages':
            with self.engine.connect() as con:
                _ = con.execute(messages.insert(), data)
        elif name == 'user_events':
            with self.engine.connect() as con:
                _ = con.execute(user_events.insert(), data)
        else:
            logger.warning("Tried to append to invalid table %s", name)

    def update_data(self, name: str, data: MessageDict):
        data['date'] = str(data['date'])
        if name == 'messages':
            update_statement = messages.update()\
                                       .where(messages.c.message_id == data['message_id'])
            with self.engine.connect() as con:
                _ = con.execute(update_statement, data)
        elif name == 'user_events':
            update_statement = user_events.update()\
                                          .where(user_events.c.message_id == data['message_id'])
            with self.engine.connect() as con:
                _ = con.execute(update_statement, data)
        else:
            logger.warning("Tried to update to invalid table %s", name)

