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

import logging

from sqlalchemy import Column, Table, MetaData, text
from sqlalchemy.engine import Connection
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TIMESTAMP, BigInteger


logger = logging.getLogger(__name__)

metadata = MetaData()
messages = Table('messages_utc', metadata,
                 Column('date', TIMESTAMP),
                 Column('from_user', BigInteger),
                 Column('text_index_col', postgresql.TSVECTOR))

db_sql = sql = """
        create table if not exists messages_utc
        (
            message_id              bigint,
            date                    timestamptz,
            from_user               bigint,
            forward_from_message_id bigint,
            forward_from            bigint,
            forward_from_chat       bigint,
            caption                 text,
            text                    text,
            sticker_set_name        text,
            new_chat_title          text,
            reply_to_message        bigint,
            file_id                 text,
            type                    text
        );
        
        alter table messages_utc
                add column if not exists text_index_col tsvector
                generated always as (to_tsvector('english', coalesce(text, ''))) stored;
        
        create index if not exists text_idx
            on messages_utc using gin (text_index_col);
        
        create index if not exists messages_utc_date_index
            on messages_utc (date);
        
        create index if not exists messages_utc_from_user_index
            on messages_utc (from_user);
        
        create index if not exists messages_utc_type_index
            on messages_utc (type);
            
        create table if not exists user_events
        (
            message_id bigint,
            user_id    bigint,
            date       timestamptz,
            event      text
        );
        
        -- Migrate wrong column type
        alter table user_events alter column user_id type bigint using user_id::bigint;
        
        create index if not exists ix_user_events_message_id
            on user_events (message_id);
        
        create table if not exists user_names
        (
            user_id  bigint,
            date     timestamptz,
            username text,
            display_name text
        );
        
        create index if not exists user_names_user_id_date_index
            on user_names (user_id, date);
        
        """


def init_dbs(con: Connection):
    con.execute(text(db_sql))
