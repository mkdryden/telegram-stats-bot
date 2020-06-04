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

media_dict = {'sticker': 'sticker',
              'animation': 'animation',
              'video_file': 'video',
              'voice_message': 'voice',
              'audio_file': 'audio',
              'video_message': 'video_note'}

user_event_cat = pd.Categorical(['left', 'joined'])
message_type_cat = pd.Categorical(['migrate_from_group', 'text', 'pinned_message', 'photo', 'sticker',
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


def convert_messages(df: pd.DataFrame) -> typing.Tuple[typing.List[dict], typing.List[dict]]:
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
                message_dict['from_user'] = message.from_id

            if pd.notnull(message.forwarded_from):
                try:
                    message_dict['forward_from'] = int(message.forwarded_from)
                except ValueError:
                    pass

            if pd.notnull(message.reply_to_message_id):
                message_dict['reply_to_message'] = message.reply_to_message_id

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
            elif pd.notnull(message.location_information):
                message_dict['type'] = 'location'

        elif message.type == 'service':
            if pd.notnull(message.actor_id):
                message_dict['from_user'] = message.actor_id

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
                                          'event': 'join'})
                except TypeError:
                    user_event_dict = {'message_id': message.id,
                                       'user_id': message.actor_id,
                                       'date': message.date,
                                       'event': 'join'}
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
    return messages_out, users_out


def parse_json(path: str):
    with open(path, encoding='utf-8') as f:
        js = json.load(f)
    chat = js['chats']['list'][1]['messages']
    df = pd.DataFrame(chat)
