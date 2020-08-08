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

import re

md_match = re.compile(r"(\[[^][]*]\(http[^()]*\))|([_*[\]()~>#+-=|{}.!\\])")


def escape_markdown(string: str) -> str:
    def url_match(match: re.Match):
        if match.group(1):
            return f'{match.group(1)}'
        return f'\\{match.group(2)}'

    return re.sub(md_match, url_match, string)
