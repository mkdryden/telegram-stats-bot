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
import string
import secrets
import re

from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement
from sqlalchemy.sql.base import ColumnCollection


md_match = re.compile(r"(\[[^][]*]\(http[^()]*\))|([_*[\]()~>#+-=|{}.!\\])")


def escape_markdown(string: str) -> str:
    def url_match(match: re.Match):
        if match.group(1):
            return f'{match.group(1)}'
        return f'\\{match.group(2)}'

    return re.sub(md_match, url_match, string)


# Modified from https://stackoverflow.com/a/49726653/3946475
class TsStat(FunctionElement):
    name = "ts_stat"

    @property
    def columns(self):
        word = Column('word', Text)
        ndoc = Column('ndoc', Integer)
        nentry = Column('nentry', Integer)
        return ColumnCollection(columns=((col.name, col) for col in (word, ndoc, nentry)))


@compiles(TsStat, 'postgresql')
def pg_ts_stat(element, compiler, **kw):
    kw.pop("asfrom", None)  # Ignore and set explicitly
    arg1, = element.clauses
    # arg1 is a FromGrouping, which would force parens around the SELECT.
    stmt = compiler.process(
        arg1.element, asfrom=False, literal_binds=True, **kw)

    return f"ts_stat({random_quote(stmt)})"


def random_quote(statement: str) -> str:
    quote_str = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(8))  # Randomize dollar quotes
    return f"${quote_str}${statement}${quote_str}$"
