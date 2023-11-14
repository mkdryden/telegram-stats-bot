from sqlalchemy import text, inspect
from tests.conftest import n_rows


def test_db_load(db_connection):
    """Check main postgresql fixture."""
    assert set(inspect(db_connection).get_table_names()) == {'messages_utc', 'user_events', 'user_names'}
    with db_connection.connect() as con:
        assert con.execute(text("select count(*) from messages_utc")).fetchone()[0] == n_rows
