import datetime
import secrets
from datetime import timedelta, timezone
import json

import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine, text, NullPool, Engine
from random_word.services.local import Local

from telegram_stats_bot.db import db_sql
from telegram_stats_bot.log_storage import messages, user_names


class RandomWords(Local):
    def __init__(self):
        super().__init__()
        with open(self.source) as word_database:
            self.words = list(json.load(word_database).keys())  # Cache loaded file

    def get_random_word(self):
        """
        Parent implementation reloads json every time, which is slow.
        """
        return secrets.choice(self.words)


def generate_user_names(n_users=10) -> list[dict]:
    random_words = RandomWords()
    start_date = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    return [{'user_id': n,
             'date': start_date,
             'username': '@' + random_words.get_random_word(),
             'display_name': random_words.get_random_word()}
            for n in range(n_users)]


def generate_message_data(n_rows=5000, n_users=10, n_titles=3) -> list[dict]:
    random_words = RandomWords()
    start_date = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    chat = [{'message_id': n,
             'date': start_date + timedelta(hours=n),
             'from_user': n % n_users,
             'forward_from_message_id': None,
             'forward_from': None,
             'forward_from_chat': None,
             'caption': None,
             'text': ' '.join([random_words.get_random_word() for _ in range(10)]),
             'sticker_set_name': None,
             'new_chat_title': None,
             'reply_to_message': None,
             'file_id': None,
             'type': 'text'}
            for n in range(n_rows)]

    # Add new chat titles
    for t in [n_rows//n_titles * n for n in range(n_titles)]:
        chat[t]['type'] = 'new_chat_title'
        chat[t]['new_chat_title'] = random_words.get_random_word()
        chat[t]['text'] = None
    return chat


n_users = 10
n_rows = 5000
user_table = generate_user_names(n_users)
message_table = generate_message_data(n_rows=n_rows, n_users=n_users)


def load_database(**kwargs):
    engine = create_engine("postgresql+psycopg://" +
                           f"postgres:{kwargs['password']}@{kwargs['host']}:{kwargs['port']}/{kwargs['dbname']}")
    with engine.connect() as con:
        con.execute(text(db_sql))
        con.execute(user_names.insert(), user_table)
        con.execute(messages.insert(), message_table)
        con.commit()


psql_proc_loaded = factories.postgresql_proc(
    load=[load_database],
)

psql_loaded = factories.postgresql(
    "psql_proc_loaded",
)


@pytest.fixture
def db_connection(psql_loaded) -> Engine:
    """Return a database connection."""
    connection = f'postgresql+psycopg://{psql_loaded.info.user}:@{psql_loaded.info.host}:' +\
                 f'{psql_loaded.info.port}/{psql_loaded.info.dbname}'
    engine = create_engine(connection, echo=False, poolclass=NullPool)
    return engine
