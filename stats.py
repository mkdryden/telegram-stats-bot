import logging
from typing import Dict, List, Tuple, Text, NoReturn
from threading import Lock
from io import BytesIO
import argparse
import inspect
import re

import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from sqlalchemy.engine import Engine

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
                       'history': "get_message_history"}

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
            query = f"""
            UPDATE user_names
            SET username = '{username}'
            WHERE user_id = {uid} AND username IS DISTINCT FROM '{username}';
            """
            if display_name:
                query += f"""\n
                         INSERT INTO user_names(user_id, date, username, display_name)
                             VALUES ({uid}, current_timestamp, '{username}', '{display_name}');
                         """

            with self.engine.connect() as con:
                con.execute(query)

    def get_chat_counts(self, n: int = None, start: str = None, end: str = None) -> Tuple[str, None]:
        """
        Get top chat users
        :param n: Number of users to show
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :return:
        """
        date_query = None

        if n is not None:
            if n <= 0:
                raise HelpException(f'n must be greater than 0, got: {n}')
        else:
            n = 20

        if start:
            start_dt = pd.to_datetime(start)
            date_query = f"WHERE date >= '{start_dt}'"

        if end:
            end_dt = pd.to_datetime(end)
            if date_query:
                date_query += f" AND date < '{end_dt}'"
            else:
                date_query = f"WHERE date < '{end_dt}'"

        query = f"""
                SELECT "from_user", COUNT(*)
                FROM "messages_utc"
                {date_query}
                GROUP BY "from_user"
                ORDER BY "count" DESC;
                """
        with self.engine.connect() as con:
            df = pd.read_sql_query(query, con, index_col='from_user')

        user_df = pd.Series(self.users, name="user")
        user_df = user_df.apply(lambda x: x[0])  # Take only @usernames
        df = df.join(user_df)
        df['Percent'] = df['count'] / df['count'].sum() * 100
        df = df[['user', 'count', 'Percent']]
        df.columns = ['User', 'Total Messages', 'Percent']
        df['User'] = df['User'].str.replace(r'[^\x00-\x7F]', "", regex=True)

        return df.iloc[:n].to_string(index=False, header=True, float_format=lambda x: f"{x:.1f}"), None

    def get_counts_by_hour(self, user: Tuple[int, str] = None, start: str = None, end: str = None)\
            -> Tuple[None, BytesIO]:
        """
        Get plot of messages for hours of the day
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        query_conditions = []

        if start:
            start_dt = pd.to_datetime(start)
            query_conditions.append(f"date >= '{start_dt}'")

        if end:
            end_dt = pd.to_datetime(end)
            query_conditions.append(f"date < '{end_dt}'")

        if user:
            query_conditions.append(f"from_user = {user[0]}")

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
            df = pd.read_sql_query(query, con)

        df['day'] = pd.to_datetime(df.day)
        df['day'] = df.day.dt.tz_convert(self.tz)
        df = df.set_index('day')
        df = df.asfreq('h', fill_value=0)  # Insert 0s for periods with no messages
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
        subplot.set_xlim(-1, 24)

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

    def get_counts_by_day(self, user: Tuple[int, str] = None, start: str = None, end: str = None, plot: str = None)\
            -> Tuple[None, BytesIO]:
        """
        Get plot of messages for days of the week
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param plot: Type of plot. ('box' or 'violin')
        """
        query_conditions = []

        if start:
            start_dt = pd.to_datetime(start)
            query_conditions.append(f"date >= '{start_dt}'")

        if end:
            end_dt = pd.to_datetime(end)
            query_conditions.append(f"date < '{end_dt}'")

        if user:
            query_conditions.append(f"from_user = {user[0]}")

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
            df = pd.read_sql_query(query, con)

        df['day'] = pd.to_datetime(df.day)
        df['day'] = df.day.dt.tz_convert(self.tz)
        df = df.set_index('day')
        df = df.asfreq('d', fill_value=0)  # Fill periods with no messages
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

    def get_week_by_hourday(self, user: Tuple[int, str] = None, start: str = None, end: str = None)\
            -> Tuple[None, BytesIO]:
        """
        Get plot of messages over the week by day and hour.
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        query_conditions = []

        if start:
            start_dt = pd.to_datetime(start)
            query_conditions.append(f"date >= '{start_dt}'")

        if end:
            end_dt = pd.to_datetime(end)
            query_conditions.append(f"date < '{end_dt}'")

        if user:
            query_conditions.append(f"from_user = {user[0]}")

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
            df = pd.read_sql_query(query, con)

        df['msg_time'] = pd.to_datetime(df.msg_time)
        df['msg_time'] = df.msg_time.dt.tz_convert('America/Toronto')
        df = df.set_index('msg_time')
        df = df.asfreq('h', fill_value=0)  # Fill periods with no messages
        df['dow'] = df.index.weekday
        df['hour'] = df.index.hour
        df['day_name'] = df.index.day_name()
        df_grouped = df[['messages', 'hour', 'day_name']].groupby(['hour', 'day_name']).sum().unstack()
        df_grouped = df_grouped.loc[:, 'messages']
        df_grouped = df_grouped[['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                                 'Friday', 'Saturday', 'Sunday']]

        fig = Figure(constrained_layout=True)
        ax = fig.subplots()

        # Number labels are too big if more than 3 digits
        if df_grouped.max().max() > 999:
            annot = False
        else:
            annot = True

        sns.heatmap(df_grouped.T, yticklabels=['M', 'T', 'W', 'Th', 'F', 'Sa', 'Su'], linewidths=.5,
                    square=True, annot=annot, fmt='d', annot_kws={'size': 8},
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

    def get_message_history(self, user: Tuple[int, str] = None, averages: int = None, start: str = None, end: str = None)\
            -> Tuple[None, BytesIO]:
        """
        Make a plot of message history over time
        :param averages: Moving average width (in days)
        :param start: Start timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        :param end: End timestamp (e.g. 2019, 2019-01, 2019-01-01, "2019-01-01 14:21")
        """
        query_conditions = []
        if averages is None:
            averages = 30

        if start:
            start_dt = pd.to_datetime(start)
            query_conditions.append(f"date >= '{start_dt}'")

        if end:
            end_dt = pd.to_datetime(end)
            query_conditions.append(f"date < '{end_dt}'")

        if user:
            query_conditions.append(f"from_user = {user[0]}")

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
            df = pd.read_sql_query(query, con)
        df['day'] = pd.to_datetime(df.day)
        df['day'] = df.day.dt.tz_convert(self.tz)
        if averages:
            df['msg_rolling'] = df['messages'].rolling(averages, center=True).mean()

        fig = Figure()  # TODO: One day pandas will let you use constrained_layout=True here...
        subplot = fig.subplots()
        df.plot(x='day', y='messages', alpha=0.5, legend=False, ax=subplot)
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
            else:
                if doc:
                    arg_doc = None
                    for line in doc:
                        match = re.match(rf"^:param {arg.name}: (.*)", line)
                        if match:
                            arg_doc = match.group(1)
                subparser.add_argument(f"-{arg.name}", type=arg.annotation, help=arg_doc)

    return parser
