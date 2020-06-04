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

import sys

from typing import Tuple, Union, List
if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from datetime import datetime

import telegram


class MessageDict(TypedDict):
    message_id: int
    date: Union[str, datetime]
    from_user: int
    forward_from_message_id: Union[int, None]
    forward_from: Union[int, None]
    forward_from_chat: Union[int, None]
    caption: Union[str, None]
    text: Union[str, None]
    sticker_set_name: Union[str, None]
    new_chat_title: Union[str, None]
    reply_to_message: Union[int, None]
    file_id: Union[str, None]
    type: str


def parse_message(message: telegram.message.Message) -> Tuple[dict, List[dict]]:
    message_dict: MessageDict = {'message_id': message.message_id,
                                 'date': message.date,
                                 'from_user': None,
                                 'forward_from_message_id': message.forward_from_message_id,
                                 'forward_from': None,
                                 'forward_from_chat': None,
                                 'caption': message.caption,
                                 'text': message.text,
                                 'sticker_set_name': None,
                                 'new_chat_title': message.new_chat_title,
                                 'reply_to_message': None,
                                 'file_id': None,
                                 'type': None,
                                 }
    user_event_dict = [{}]

    if message.from_user:
        message_dict['from_user'] = message.from_user.id

    if message.forward_from:
        try:
            message_dict['forward_from'] = message.forward_from.id
        except AttributeError:
            pass
        try:
            message_dict['forward_from_chat'] = message.forward_from_chat.id
        except AttributeError:
            pass

    if message.reply_to_message:
        message_dict['reply_to_message'] = message.reply_to_message.message_id

    if message.text:
        message_dict['type'] = 'text'
    elif message.animation:
        message_dict['type'] = 'animation'
        message_dict['file_id'] = message.animation.file_id
    elif message.audio:
        message_dict['type'] = 'audio'
        message_dict['file_id'] = message.audio.file_id
    elif message.document:
        message_dict['type'] = 'document'
        message_dict['file_id'] = message.document.file_id
    elif message.game:
        message_dict['type'] = 'game'
    elif message.photo:
        message_dict['type'] = 'photo'
    elif message.sticker:
        message_dict['type'] = 'sticker'
        message_dict['file_id'] = message.sticker.file_id
        message_dict['sticker_set_name']: message.sticker.set_name
    elif message.video:
        message_dict['type'] = 'video'
    elif message.video_note:
        message_dict['type'] = 'video_note'
    elif message.voice:
        message_dict['type'] = 'voice'
    elif message.location:
        message_dict['type'] = 'location'
    elif message.poll:
        message_dict['type'] = 'poll'
    elif message.new_chat_title:
        message_dict['type'] = 'new_chat_title'
    elif message.new_chat_photo:
        message_dict['type'] = 'new_chat_photo'
    elif message.pinned_message:
        message_dict['type'] = 'pinned_message'
    elif message.new_chat_members:
        message_dict['type'] = 'new_chat_members'
        member: telegram.user.User
        user_event_dict = [{'message_id': message.message_id,
                            'user_id': u_id,
                            'date': message.date,
                            'event': 'joined'}
                           for u_id in [member.id for member in message.new_chat_members]]
    elif message.left_chat_member:
        message_dict['type'] = 'left_chat_member'
        user_event_dict = [{'message_id': message.message_id,
                            'user_id': message.left_chat_member.id,
                            'date': message.date,
                            'event': 'left'}]

    return message_dict, user_event_dict
