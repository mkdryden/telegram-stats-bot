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

import json
import typing

import pandas as pd
import sqlalchemy.engine
import typer
from sqlalchemy import create_engine

from .stats import StatsRunner

media_dict = {'sticker': 'sticker',
              'animation': 'animation',
              'video_file': 'video',
              'voice_message': 'voice',
              'audio_file': 'audio',
              'video_message': 'video_note'}

user_event_cat = pd.CategoricalDtype(['left', 'joined'])
message_type_cat = pd.CategoricalDtype(['migrate_from_group', 'text', 'pinned_message', 'photo', 'sticker',
                                   'new_chat_members', 'left_chat_member', 'animation', 'video',
                                   'location', 'new_chat_title', 'voice', 'audio',
                                   'new_chat_photo', 'video_note', 'poll'])


def text_list_parser(text: typing.Union[str, typing.Sequence]) -> str:
    if isinstance(text, str):
        return text
    out = ""
    for block in text:
        try:
            out += block['text']
        except TypeError:
            out += block
    return out


def convert_messages(df: pd.DataFrame) -> typing.Tuple[typing.List[dict], typing.List[dict], dict]:
    messages_out = []
    users_out = []

    for message in df.itertuples():
        message_dict = {'message_id': message.id,
                        'date': message.date,
                        'from_user': None,
                        'forward_from_message_id': None,
                        'forward_from': None,
                        'forward_from_chat': None,
                        'caption': "",
                        'text': "",
                        'sticker_set_name': "",
                        'new_chat_title': "",
                        'reply_to_message': None,
                        'file_id': None,
                        'type': None,
                        }
        user_event_dict = {}
        if message.type == 'message':
            if pd.notnull(message.from_id):
                if not message.from_id.startswith('user'):
                    continue
                message_dict['from_user'] = int(message.from_id[4:])  # remove 'user' from id

            if pd.notnull(message.forwarded_from):
                try:
                    message_dict['forward_from'] = int(message.from_id[4:])  # username is used in forwarded_from
                except ValueError:
                    pass

            if pd.notnull(message.reply_to_message_id):
                message_dict['reply_to_message'] = int(message.reply_to_message_id)

            if pd.notnull(message.photo):
                message_dict['type'] = 'photo'
                if message.text != "":
                    message_dict['caption'] = text_list_parser(message.text)
            elif pd.notnull(message.media_type):
                if message.text != "":
                    message_dict['caption'] = text_list_parser(message.text)
                message_dict['type'] = media_dict[message.media_type]
                if message.media_type == 'sticker' and '.webp' not in message.file:
                    message_dict['file_id'] = message.file
            elif message.text != "":
                message_dict['type'] = 'text'
                message_dict['text'] = text_list_parser(message.text)
            elif pd.notnull(message.poll):
                message_dict['type'] = 'poll'

        elif message.type == 'service':
            if pd.notnull(message.actor_id):
                if message.actor_id.startswith('user'):
                    message_dict['from_user'] = int(message.actor_id[4:])

            if message.action == 'edit_group_title':
                message_dict['type'] = 'new_chat_title'
                message_dict['new_chat_title'] = message.title
            elif message.action == 'pin_message':
                message_dict['type'] = 'pinned_message'
            elif message.action == 'edit_group_photo':
                message_dict['type'] = 'new_chat_photo'
            elif message.action == 'invite_members' or message.action == 'join_group_by_link':
                message_dict['type'] = 'new_chat_members'
                try:
                    for i in message.members:
                        users_out.append({'message_id': message.id,
                                          'user_id': i,
                                          'date': message.date,
                                          'event': 'joined'})
                except TypeError:
                    user_event_dict = {'message_id': message.id,
                                       'user_id': message.actor_id,
                                       'date': message.date,
                                       'event': 'joined'}
            elif message.action == 'remove_members':
                message_dict['type'] = 'left_chat_member'
                for i in message.members:
                    users_out.append({'message_id': message.id,
                                      'user_id': i,
                                      'date': message.date,
                                      'event': 'left'})
            else:
                message_dict['type'] = message.action
        messages_out.append(message_dict)
        if user_event_dict != {}:
            users_out.append(user_event_dict)

    user_map = {int(i[4:]): df.loc[df['from_id'] == i, 'from'].iloc[0]
                for i in df['from_id'].unique()
                if (df['from_id'] == i).any() and i.startswith('user')}

    # Use long name for both name and long name since we can't fetch usernames
    user_map = {k: (v, v) for k, v in user_map.items() if v}

    return messages_out, users_out, user_map


def parse_json(path: str):
    with open(path, encoding='utf-8') as f:
        js = json.load(f)
    chat = js['chats']['list'][1]['messages']
    df = pd.DataFrame(chat)


def fix_dtypes_m(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    intcols = ['forward_from_message_id', 'forward_from', 'forward_from_chat',
               'from_user', 'reply_to_message']
    df_out = df.copy()
    df_out.loc[:, intcols] = df_out.loc[:, intcols].astype('Int64')
    df_out.loc[:, 'date'] = pd.to_datetime(df_out['date'], utc=False).dt.tz_localize(tz=tz,
                                                                                     ambiguous=True)
    df_out.loc[:, 'type'] = df_out.loc[:, 'type'].astype(message_type_cat)
    return df_out.convert_dtypes()


def fix_dtypes_u(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    df_out = df.copy()
    df_out.loc[:, 'date'] = pd.to_datetime(df_out['date'], utc=False).dt.tz_localize(tz=tz,
                                                                                     ambiguous=True)
    df_out.loc[df_out.event == 'join', 'event'] = 'joined'
    df_out['event'] = df_out.event.astype(user_event_cat)

    return df_out.convert_dtypes()


def update_user_list(users: dict[int, tuple[str, str]],  engine: sqlalchemy.engine.Engine, tz: str):
    stats_runner = StatsRunner(engine, tz)
    stats_runner.update_user_ids(users)

def main(json_path: str, db_url: str, tz: str = 'Etc/UTC'):
    """
    Parse backup json file and update database with contents.
    :param json_path:
    :param db_url:
    :param tz:
    :return:
    """
    with open(json_path, encoding='utf-8') as f:
        js = json.load(f)

    chat = js['messages']
    messages, users, user_map = convert_messages(pd.DataFrame(chat))

    df_m = pd.DataFrame(messages).set_index('message_id')
    df_m = fix_dtypes_m(df_m, tz)
    df_u = pd.DataFrame(users).set_index('message_id')
    df_u = fix_dtypes_u(df_u, tz)

    engine = create_engine(db_url, echo=False)

    # Exclude existing messages
    m_ids = pd.read_sql_table('messages_utc', engine).message_id
    df_m = df_m.loc[~df_m.index.isin(m_ids)]

    # Map usernames back to numeric ids
    inverse_user_map = pd.DataFrame(user_map).T.reset_index()
    df_u = df_u.reset_index().merge(inverse_user_map, how='inner', left_on='user_id', right_on=0) \
               .loc[:, ['index', 'message_id', 'date', 'event']] \
               .rename(columns={'index': 'user_id'}) \
               .set_index('message_id', drop=True)

    # Merge existing user events
    m_ids = pd.read_sql_table('user_events', engine).set_index('message_id')
    df_u['user_id'] = df_u['user_id'].astype('Int64')
    merged = df_u.merge(m_ids, how='outer', left_index=True, right_index=True, suffixes=('', 'y'))
    merged['user_idy'] = pd.to_numeric(merged['user_idy'], errors='coerce').astype('Int64')  # Keep existing valid IDs
    merged['user_id'] = merged['user_id'].fillna(merged['user_idy'])
    df_u = merged.loc[:, ['user_id', 'date', 'event']].dropna(how='any')

    df_u.to_sql('user_events', engine, if_exists='replace')  # Contains possible updates to existing values
    df_m.to_sql('messages_utc', engine, if_exists='append')

    update_user_list(user_map, engine, tz)


if __name__ == '__main__':
    typer.run(main)
