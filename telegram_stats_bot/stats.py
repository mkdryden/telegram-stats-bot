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
from typing import Dict, List, Tuple, Text, NoReturn
from threading import Lock
from io import BytesIO
import argparse
import inspect
import re
from datetime import timedelta, datetime

import pandas as pd
import seaborn as sns
import numpy as np
from matplotlib.figure import Figure
from matplotlib.dates import date2num
from sqlalchemy.engine import Engine

from .utils import escape_markdown

sns.set_context('paper')
sns.set_style('whitegrid')
sns.set_palette("Set2")

logger = logging.getLogger()


class HelpException(Exception):
    def __init__(self, msg: str = None):
        self.msg = msg


class InternalParser(argparse.ArgumentParser):
    def error(self, message: Text) -> NoReturn:
        try:
            raise  # Reraises mostly ArgumentError for bad arg
        except RuntimeError:
            raise HelpException(message)

    def print_help(self, file=None) -> None:
        raise HelpException(self.format_help())

    def exit(self, status=None, message=None):
        pass


class StatsRunner(object):
    allowed_methods = {'counts': "get_chat_counts",
                       'hours': "get_counts_by_hour",
                       'days': "get_counts_by_day",
                       'week': "get_week_by_hourday",
                       'history': "get_message_history",
                       'titles': 'get_title_history',
                       'corr': "get_user_correlation",
                       'delta': "get_message_deltas",
                       'types': "get_type_stats",
                       'random': "get_random_message"}

    def __init__(self, engine: Engine, tz: str = 'America/Toronto'):
        self.engine = engine
        self.tz = tz

        self.users: Dict[int, Tuple[str, str]] = self.get_db_users()
        self.users_lock = Lock()

    def get_message_user_ids(self) -> List[int]:
        with self.engine.connect() as con:
            result = con.execute("SELECT DISTINCT from_user FROM messages_utc;")
        return [user for user, in result.fetchall()]

    def get_db_users(self) -> Dict[int, Tuple[str, str]]:
        query = """
        select user_id, username, display_name from (
            select
                *,
                row_number() over(partition by user_id order by date desc) as rn
            from
                user_names
            ) t
        where t.rn = 1
        """

        with self.engine.connect() as con:
            result = con.execute(query)
        result = result.fetchall()

        return {user_id: (username, name) for user_id, username, name in result}

    def update_user_ids(self, user_dict: Dict[int, Tuple[str, str]]):
        for uid in user_dict:
            username, display_name = user_dict[uid]
            sql_dict = {'uid': uid, 'username': username, 'display_name': display_name}
            query = """
            UPDATE user_names
            SET username = %(username)s
            WHERE user_id = %(uid)s AND username IS DISTINCT FROM %(username)s;
            """
            if display_name:
                query += """\n
                         INSERT INTO user_names(user_id, date, username, display_name)
                             VALUES (%(uid)s, current_timestamp, %(username)s, %(display_name)s);
                         """

            with self.engine.connect() as con:
                con.execute(query, sql_dict)

    def get_chat_counts(self, n: int = 20, start: str = None, end: str = None) -> Tuple[str, None]:
        """
        Get top chat users
        :param n: Number of users to show
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :return:
        """
        date_query = None
        sql_dict = {}
        query_conditions = []

        if n <= 0:
            raise HelpException(f'n must be greater than 0, got: {n}')

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        query_where = ""
        if query_conditions:
            query_where = f"WHERE {' AND '.join(query_conditions)}"

        query = f"""
                SELECT "from_user", COUNT(*)
                FROM "messages_utc"
                {query_where}
                GROUP BY "from_user"
                ORDER BY "count" DESC;
                """
        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict, index_col='from_user')

        user_df = pd.Series(self.users, name="user")
        user_df = user_df.apply(lambda x: x[0])  # Take only @usernames
        df = df.join(user_df)
        df['Percent'] = df['count'] / df['count'].sum() * 100
        df = df[['user', 'count', 'Percent']]
        df.columns = ['User', 'Total Messages', 'Percent']
        df['User'] = df['User'].str.replace(r'[^\x00-\x7F]', "", regex=True)  # Drop emoji

        text = df.iloc[:n].to_string(index=False, header=True, float_format=lambda x: f"{x:.1f}")

        return f"```\n{text}\n```", None

    def get_counts_by_hour(self, user: Tuple[int, str] = None, start: str = None, end: str = None) \
            -> Tuple[None, BytesIO]:
        """
        Get plot of messages for hours of the day
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        query_conditions = []
        sql_dict = {}

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        if user:
            sql_dict['user'] = user[0]
            query_conditions.append("from_user = %(user)s")

        query_where = ""
        if query_conditions:
            query_where = f"WHERE {' AND '.join(query_conditions)}"

        query = f"""
                 SELECT date_trunc('hour', date) as day, count(*) as messages
                 FROM messages_utc
                 {query_where}
                 GROUP BY day
                 ORDER BY day
                 """

        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict)

        df['day'] = pd.to_datetime(df.day)
        df['day'] = df.day.dt.tz_convert(self.tz)
        df = df.set_index('day')
        df = df.asfreq('h', fill_value=0)  # Insert 0s for periods with no messages

        if (df.index.max() - df.index.min()) < pd.Timedelta('24 hours'):  # Deal with data covering < 24 hours
            df = df.reindex(pd.date_range(df.index.min(), periods=24, freq='h'))

        df['hour'] = df.index.hour

        if user:
            # Aggregate over 1 week periods
            df = df.groupby('hour').resample('7D').sum().drop(columns='hour')
            df['hour'] = df.index.get_level_values('hour')

        fig = Figure(constrained_layout=True)
        subplot = fig.subplots()

        sns.stripplot(x='hour', y='messages', data=df, jitter=.4, size=2, ax=subplot, alpha=.5, zorder=0)
        sns.boxplot(x='hour', y='messages', data=df, whis=1, showfliers=False, whiskerprops={"zorder": 10},
                    boxprops={"zorder": 10},
                    ax=subplot, zorder=10)
        subplot.set_ylim(bottom=0, top=df['messages'].quantile(0.999, interpolation='higher'))

        subplot.axvspan(11.5, 23.5, zorder=0, color=(0, 0, 0, 0.05))
        subplot.set_xlim(-1, 24)  # Set explicitly to plot properly even with missing data

        if user:
            subplot.set_ylabel('Messages per Week')
            subplot.set_title(f"Messages by Hour for {user[1]}")
        else:
            subplot.set_ylabel('Messages per Day')
            subplot.set_title("Messages by Hour")

        sns.despine(fig=fig)

        bio = BytesIO()
        bio.name = 'plot.png'
        fig.savefig(bio, bbox_inches='tight')
        bio.seek(0)

        return None, bio

    def get_counts_by_day(self, user: Tuple[int, str] = None, start: str = None, end: str = None, plot: str = None) \
            -> Tuple[None, BytesIO]:
        """
        Get plot of messages for days of the week
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param plot: Type of plot. ('box' or 'violin')
        """
        query_conditions = []
        sql_dict = {}

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        if user:
            sql_dict['user'] = user[0]
            query_conditions.append("from_user = %(user)s")

        query_where = ""
        if query_conditions:
            query_where = f"WHERE {' AND '.join(query_conditions)}"

        query = f"""
                 SELECT date_trunc('day', date)
                     as day, count(*) as messages
                 FROM messages_utc
                 {query_where}
                 GROUP BY day
                 ORDER BY day
                 """

        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict)

        df['day'] = pd.to_datetime(df.day)
        df['day'] = df.day.dt.tz_convert(self.tz)
        df = df.set_index('day')
        df = df.asfreq('d', fill_value=0)  # Fill periods with no messages
        if (df.index.max() - df.index.min()) < pd.Timedelta('7 days'):  # Deal with data covering < 7 days
            df = df.reindex(pd.date_range(df.index.min(), periods=7, freq='d'))
        df['dow'] = df.index.weekday
        df['day_name'] = df.index.day_name()
        df = df.sort_values('dow')  # Make sure start is Monday

        fig = Figure(constrained_layout=True)
        subplot = fig.subplots()
        if plot == 'box':
            sns.boxplot(x='day_name', y='messages', data=df, whis=1, showfliers=False, ax=subplot)
        elif plot == 'violin' or plot is None:
            sns.violinplot(x='day_name', y='messages', data=df, cut=0, inner="box", scale='width', ax=subplot)
        else:
            raise HelpException("plot must be either box or violin")
        subplot.axvspan(4.5, 6.5, zorder=0, color=(0, .8, 0, 0.1))
        subplot.set_xlabel('')
        subplot.set_ylabel('Messages per Day')
        subplot.set_xlim(-0.5, 6.5)  # Need to set this explicitly to show full range of days with na data
        if user:
            subplot.set_title(f"Messages by Day of Week for {user[1]}")
        else:
            subplot.set_title("Messages by Day of Week")

        sns.despine(fig=fig)

        bio = BytesIO()
        bio.name = 'plot.png'
        fig.savefig(bio, bbox_inches='tight')
        bio.seek(0)

        return None, bio

    def get_week_by_hourday(self, user: Tuple[int, str] = None, start: str = None, end: str = None) \
            -> Tuple[None, BytesIO]:
        """
        Get plot of messages over the week by day and hour.
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        query_conditions = []
        sql_dict = {}

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        if user:
            sql_dict['user'] = user[0]
            query_conditions.append("from_user = %(user)s")

        query_where = ""
        if query_conditions:
            query_where = f"WHERE {' AND '.join(query_conditions)}"

        query = f"""
                 SELECT date_trunc('hour', date)
                     as msg_time, count(*) as messages
                 FROM messages_utc
                 {query_where}
                 GROUP BY msg_time
                 ORDER BY msg_time
                 """
        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict)

        df['msg_time'] = pd.to_datetime(df.msg_time)
        df['msg_time'] = df.msg_time.dt.tz_convert('America/Toronto')
        df = df.set_index('msg_time')
        df = df.asfreq('h', fill_value=0)  # Fill periods with no messages
        df['dow'] = df.index.weekday
        df['hour'] = df.index.hour
        df['day_name'] = df.index.day_name()
        df_grouped = df[['messages', 'hour', 'day_name']].groupby(['hour', 'day_name']).sum().unstack()
        df_grouped = df_grouped.loc[:, 'messages']
        df_grouped = df_grouped.reindex(columns=['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                                                 'Friday', 'Saturday', 'Sunday'])

        fig = Figure(constrained_layout=True)
        ax = fig.subplots()

        sns.heatmap(df_grouped.T, yticklabels=['M', 'T', 'W', 'Th', 'F', 'Sa', 'Su'], linewidths=.5,
                    square=True, fmt='d', vmin=0,
                    cbar_kws={"orientation": "horizontal"}, cmap="viridis", ax=ax)
        ax.tick_params(axis='y', rotation=0)
        ax.set_ylabel("")
        ax.set_xlabel("")
        if user:
            ax.set_title(f"Total messages by day and hour for {user[1]}")
        else:
            ax.set_title("Total messages by day and hour")

        bio = BytesIO()
        bio.name = 'plot.png'
        fig.savefig(bio, bbox_inches='tight')
        bio.seek(0)

        return None, bio

    def get_message_history(self, user: Tuple[int, str] = None, averages: int = None, start: str = None,
                            end: str = None) \
            -> Tuple[None, BytesIO]:
        """
        Make a plot of message history over time
        :param averages: Moving average width (in days)
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        query_conditions = []
        sql_dict = {}

        if averages:
            if averages < 0:
                raise HelpException("averages must be >= 0")

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        if user:
            sql_dict['user'] = user[0]
            query_conditions.append("from_user = %(user)s")

        query_where = ""
        if query_conditions:
            query_where = f"WHERE {' AND '.join(query_conditions)}"

        query = f"""
                    SELECT date_trunc('day', date)
                        as day, count(*) as messages
                    FROM messages_utc
                    {query_where}
                    GROUP BY day
                    ORDER BY day
                 """

        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict)
        df['day'] = pd.to_datetime(df.day)
        df['day'] = df.day.dt.tz_convert(self.tz)

        if averages is None:
            averages = len(df) // 20
            if averages <= 1:
                averages = 0
        if averages:
            df['msg_rolling'] = df['messages'].rolling(averages, center=True).mean()
            alpha = 0.5
        else:
            alpha = 1

        fig = Figure()  # TODO: One day pandas will let you use constrained_layout=True here...
        subplot = fig.subplots()
        df.plot(x='day', y='messages', alpha=alpha, legend=False, ax=subplot)
        if averages:
            df.plot(x='day', y='msg_rolling', legend=False, ax=subplot)
        subplot.set_ylabel("Messages")
        subplot.set_xlabel("Date")
        if user:
            subplot.set_title(f"Message History for {user[1]}")
        else:
            subplot.set_title("Message History")
        sns.despine(fig=fig)
        fig.tight_layout()

        bio = BytesIO()
        bio.name = 'plot.png'
        fig.savefig(bio)
        bio.seek(0)

        return None, bio

    def get_title_history(self, start: str = None, end: str = None, duration: bool = False) \
            -> Tuple[None, BytesIO]:
        """
        Make a plot of group titles history over time
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param duration: If true, order by duration instead of time.
        """
        query_conditions = []
        sql_dict = {}

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        query_where = ""
        if query_conditions:
            query_where = f"AND {' AND '.join(query_conditions)}"

        query = f"""
                    SELECT date, new_chat_title
                    FROM messages_utc
                    WHERE type = 'new_chat_title' {query_where}
                    ORDER BY date;
                 """

        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict)

        df['idx'] = np.arange(len(df))
        df['diff'] = -df['date'].diff(-1)
        df['end'] = df['date'] + df['diff']

        if end:
            last = pd.Timestamp(sql_dict['end_dt'], tz=self.tz).tz_convert('utc')
        else:
            last = pd.Timestamp(datetime.now(), tz='utc')

        df_end = df['end']
        df_end.iloc[-1] = last
        df.loc[:, 'end'] = df_end
        df.loc[:, 'diff'].iloc[-1] = df.iloc[-1]['end'] - df.iloc[-1]['date']

        fig = Figure(constrained_layout=True, figsize=(12, 0.15 * len(df)))
        ax = fig.subplots()

        if duration:
            df = df.sort_values('diff')
            df = df.reset_index(drop=True)
            df['idx'] = df.index

            ax.barh(df.idx, df['diff'].dt.days, tick_label=df.new_chat_title)

            ax.margins(0.2)
            ax.set_ylabel("")
            ax.set_xlabel("Duration (days)")
            ax.set_ylim(-1, (df.idx.max() + 1))
            ax.set_title("Chat Title History")
            ax.grid(False, which='both', axis='y')
            sns.despine(fig=fig, left=True)

        else:
            x = df.iloc[:-1].end
            y = df.iloc[:-1].idx + .5

            ax.scatter(x, y, zorder=4, color=sns.color_palette()[1])

            titles = list(zip(df.date.apply(date2num),
                              df.end.apply(date2num) - df.date.apply(date2num)))

            for n, i in enumerate(titles):
                ax.broken_barh([i], (n, 1))
                ax.annotate(df.new_chat_title[n], xy=(i[0] + i[1], n), xycoords='data',
                            xytext=(10, 0), textcoords='offset points',
                            horizontalalignment='left', verticalalignment='bottom')

            ax.set_ylim(-1, (df.idx.max() + 1))
            ax.set_xlim(titles[0][0] - 1, None)

            ax.margins(0.2)
            ax.set_ylabel("")
            ax.set_xlabel("")
            ax.set_title("Chat Title History")
            ax.grid(False, which='both', axis='y')
            ax.tick_params(axis='y', which='both', labelleft=False, left=False)
            sns.despine(fig=fig, left=True)

        bio = BytesIO()
        bio.name = 'plot.png'
        fig.savefig(bio, dpi=200)
        bio.seek(0)

        return None, bio

    def get_user_correlation(self, start: str = None, end: str = None, agg: bool = True, c_type: str = None,
                             n: int = 5, thresh: float = 0.05, autouser=None, **kwargs) -> Tuple[str, None]:
        """
        Return correlations between you and other users.
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param agg: If True, calculate correlation over messages aggregated by hours of the week
        :param c_type: Correlation type to use. Either 'pearson' or 'spearman'
        :param n: Show n highest and lowest correlation scores
        :param thresh: Fraction of time bins that have data for both users to be considered valid (0-1)
        """
        user: Tuple[int, str] = kwargs['user']
        query_conditions = []
        sql_dict = {}

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        query_where = ""
        if query_conditions:
            query_where = f"WHERE {' AND '.join(query_conditions)}"

        if n <= 0:
            raise HelpException(f'n must be greater than 0, got: {n}')

        if not c_type:
            c_type = 'pearson'
        elif c_type not in ['pearson', 'spearman']:
            raise HelpException("corr must be either pearson or spearman")

        if not 0 <= thresh <= 1:
            raise HelpException(f'n must be in the range [0, 1], got: {n}')

        query = f"""
                SELECT msg_time, extract(ISODOW FROM msg_time) as dow, extract(HOUR FROM msg_time) as hour,
                       "user", messages
                FROM (
                         SELECT date_trunc('hour', date)
                                         as msg_time,
                                count(*) as messages, from_user as "user"
                         FROM messages_utc
                         {query_where}
                         GROUP BY msg_time, from_user
                         ORDER BY msg_time
                     ) t
                ORDER BY dow, hour;
                """

        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict)
        df['msg_time'] = pd.to_datetime(df.msg_time)
        df['msg_time'] = df.msg_time.dt.tz_convert(self.tz)

        # Prune irrelevant messages (not sure if this actually improves performance)
        user_first_date = df.loc[df.user == user[0], 'msg_time'].iloc[0]
        df = df.loc[df.msg_time >= user_first_date]

        df = df.set_index('msg_time')

        user_dict = {'user': {user_id: value[0] for user_id, value in self.users.items()}}
        df = df.loc[df.user.isin(list(user_dict['user'].keys()))]  # Filter out users with no names
        df = df.replace(user_dict)  # Replace user ids with names
        df['user'] = df['user'].str.replace(r'[^\x00-\x7F]', "", regex=True)

        if agg:
            df = df.pivot_table(index=['dow', 'hour'], columns='user', values='messages', aggfunc='sum')
            corrs = []
            for other_user in df.columns.values:
                if df[user[1]].sum() / df[other_user].sum() > thresh:
                    me_notna = df[user[1]].notna()
                    other_notna = df[other_user].notna()
                    idx = me_notna | other_notna
                    corrs.append(df.loc[idx, user[1]].fillna(0).corr(df.loc[idx, other_user].fillna(0)))
                else:
                    corrs.append(pd.NA)

            me = pd.Series(corrs, index=df.columns.values).sort_values(ascending=False).iloc[1:].dropna()
        else:
            df = df.pivot(columns='user', values='messages')

            if thresh == 0:
                df_corr = df.corr(method=c_type)
            else:
                df_corr = df.corr(method=c_type, min_periods=int(thresh * len(df)))
            me = df_corr[user[1]].sort_values(ascending=False).iloc[1:].dropna()

        if len(me) < 1:
            return "`Sorry, not enough data, try with -aggtimes, decrease -thresh, or use a bigger date range.`", None

        if n > len(me) // 2:
            n = int(len(me) // 2)

        text = me.to_string(header=False, float_format=lambda x: f"{x:.3f}")
        split = text.splitlines()
        text = "\n".join(['HIGHEST CORRELATION:'] + split[:n] + ['\nLOWEST CORRELATION:'] + split[-n:])

        return f"**User Correlations for {escape_markdown(user[1])}**\n```\n{text}\n```", None

    def get_message_deltas(self, start: str = None, end: str = None, n: int = 10, thresh: int = 500,
                           autouser=None, **kwargs) -> Tuple[str, None]:
        """
        Return the median difference in message time between you and other users.
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param n: Show n highest and lowest correlation scores
        :param thresh: Only consider users with at least this many message group pairs with you
        """
        user: Tuple[int, str] = kwargs['user']
        query_conditions = []
        sql_dict = {}

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        query_where = ""
        if query_conditions:
            query_where = f"AND {' AND '.join(query_conditions)}"

        if n <= 0:
            raise HelpException(f'n must be greater than 0')

        if thresh < 0:
            raise HelpException(f'n cannot be negative')

        def fetch_mean_delta(me: int, other: int, where: str, sql_dict: dict) -> Tuple[timedelta, int]:
            query = f"""
                    select percentile_cont(0.5) within group (order by t_delta), count(t_delta)
                    from(
                        select start - lag("end", 1) over (order by start) as t_delta
                        from (
                                 select min(date) as start, max(date) as "end"
                                 from (select date, from_user,
                                              (dense_rank() over (order by date) -
                                               dense_rank() over (partition by from_user order by date)
                                                  ) as grp
                                       from messages_utc
                                       where from_user in (%(me)s, %(other)s) {where}
                                       order by date
                                      ) t
                                 group by from_user, grp
                                 order by start
                        ) t1
                    ) t2;
                    """

            sql_dict['me'] = me
            sql_dict['other'] = other

            with self.engine.connect() as con:
                result = con.execute(query, sql_dict)
            output: Tuple[timedelta, int] = result.fetchall()[0]

            return output

        results = {other: fetch_mean_delta(user[0], other, query_where, sql_dict) for other in self.users
                   if user[0] != other}

        user_deltas = {self.users[other][0]: pd.to_timedelta(result[0]) for other, result in results.items()
                       if result[1] > thresh}

        me = pd.Series(user_deltas).sort_values()
        me = me.apply(lambda x: x.round('1s'))

        if len(me) < 1:
            return "\n```\nSorry, not enough data, try a bigger date range or decrease -thresh.\n```", None

        text = me.iloc[:n].to_string(header=False, index=True)

        return f"**Median message delays for {escape_markdown(user[1])} and:**\n```\n{text}\n```", None

    def get_type_stats(self, start: str = None, end: str = None, autouser=None, **kwargs) -> Tuple[str, None]:
        """
        Print table of message statistics by type.
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        user: Tuple[int, str] = kwargs['user']
        query_conditions = []
        sql_dict = {}

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        query_where = ""
        if query_conditions:
            query_where = f" AND {' AND '.join(query_conditions)}"

        query = f"""
                    SELECT type, count(*) as count
                    FROM messages_utc
                    WHERE type NOT IN ('new_chat_members', 'left_chat_member', 'new_chat_photo',
                                       'new_chat_title', 'migrate_from_group', 'pinned_message')
                          {query_where}
                    GROUP BY type
                    ORDER BY count DESC;
                 """

        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, params=sql_dict)
        df['Group Percent'] = df['count'] / df['count'].sum() * 100
        df.columns = ['type', 'Group Count', 'Group Percent']

        if user:
            sql_dict['user'] = user[0]
            query_conditions.append("from_user = %(user)s")

            query = f"""
                        SELECT type, count(*) as user_count
                        FROM messages_utc
                        WHERE type NOT IN ('new_chat_members', 'left_chat_member', 'new_chat_photo',
                                           'new_chat_title', 'migrate_from_group', 'pinned_message')
                              AND {' AND '.join(query_conditions)}
                        GROUP BY type
                        ORDER BY user_count DESC;
                     """
            with self.engine.connect() as con:
                df_u = pd.read_sql_query(query, con, params=sql_dict)
            df_u['User Percent'] = df_u['user_count'] / df_u['user_count'].sum() * 100
            df_u.columns = ['type', 'User Count', 'User Percent']

            df = df.merge(df_u, on="type", how="outer")

        a = list(zip(df.columns.values, ["Total"] + df.iloc[:, 1:].sum().to_list()))
        df = df.append({key: value for key, value in a}, ignore_index=True)
        df['Group Count'] = df['Group Count'].astype('Int64')
        try:
            df['User Count'] = df['User Count'].astype('Int64')
        except KeyError:
            pass
        text = df.to_string(index=False, header=True, float_format=lambda x: f"{x:.1f}")

        if user:
            return f"**Messages by type, {escape_markdown(user[1])} vs group:**\n```\n{text}\n```", None
        else:
            return f"**Messages by type:**\n```\n{text}\n```", None

    def get_random_message(self, start: str = None, end: str = None,
                           user: Tuple[int, str] = None, **kwargs) -> Tuple[str, None]:
        """
        Display a random message.
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        query_conditions = []
        sql_dict = {}

        if user:
            sql_dict['user'] = user[0]
            query_conditions.append("from_user = %(user)s")

        if start:
            sql_dict['start_dt'] = pd.to_datetime(start)
            query_conditions.append("date >= %(start_dt)s")

        if end:
            sql_dict['end_dt'] = pd.to_datetime(end)
            query_conditions.append("date < %(end_dt)s")

        query_where = ""
        if query_conditions:
            query_where = f"AND {' AND '.join(query_conditions)}"

        query = f"""
                SELECT date, from_user, text
                FROM messages_utc
                WHERE type = 'text'
                {query_where}
                ORDER BY RANDOM()
                LIMIT 1;
                """

        with self.engine.connect() as con:
            result = con.execute(query, sql_dict)
        date, from_user, text = result.fetchall()[0]

        return f"*On {escape_markdown(date.strftime('%Y-%m-%d'))}, {escape_markdown(self.users[from_user][0])}" \
               f" gave these words of wisdom:*\n" \
               f"{escape_markdown(text)}\n",\
               None


def get_parser(runner: StatsRunner) -> InternalParser:
    parser = InternalParser(prog="/stats")
    parser.set_defaults(func=runner.get_chat_counts)
    subparsers = parser.add_subparsers(title="Statistics:")

    for name, func in runner.allowed_methods.items():
        try:
            doc = inspect.getdoc(getattr(runner, func)).splitlines()
        except AttributeError:
            doc = None
        subparser = subparsers.add_parser(name, help=doc[0])
        subparser.set_defaults(func=getattr(runner, func))
        f_args = inspect.signature(getattr(runner, func)).parameters

        for _, arg in f_args.items():
            arg: inspect.Parameter
            if arg.name == 'self':
                continue
            if arg.name == 'user':
                group = subparser.add_mutually_exclusive_group()
                group.add_argument('-me', action='store_true', help='calculate stats for yourself')
                group.add_argument('-user', type=int, help=argparse.SUPPRESS)
            elif arg.name == 'autouser':
                subparser.set_defaults(me=True)
                subparser.add_argument('-user', type=int, help=argparse.SUPPRESS)
            elif arg.name == 'kwargs':
                pass
            else:
                arg_doc = None
                if doc:
                    for line in doc:
                        match = re.match(rf"^:param {arg.name}: (.*)", line)
                        if match:
                            arg_doc = match.group(1)

                if arg.annotation == bool:
                    subparser.add_argument(f"-{arg.name}".replace('_', '-'), action='store_true', help=arg_doc)
                else:
                    subparser.add_argument(f"-{arg.name}".replace('_', '-'), type=arg.annotation, help=arg_doc,
                                           default=arg.default)

    return parser
