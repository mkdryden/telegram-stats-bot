from io import BytesIO

from tests.conftest import n_users, n_rows, user_table
from telegram_stats_bot.stats import StatsRunner, HelpException

import pytest


@pytest.fixture
def sr(db_connection):
    return StatsRunner(db_connection)


def test_get_message_user_ids(sr):
    assert set(sr.get_message_user_ids()) == set(range(len(user_table)))


def test_get_db_users(sr):
    for k, v in sr.get_db_users().items():
        username, display_name = v
        assert username == user_table[k]['username']
        assert display_name == user_table[k]['display_name']


@pytest.mark.usefixtures('sr')
class TestChatCounts:
    def test_basic(self, sr):
        sr.get_chat_counts()

    def test_lquery(self, sr):
        sr.get_chat_counts(lquery='dogdfs')

    def test_mtype_valid(self, sr):
        assert sr.get_chat_counts(mtype='text')[0].count('\n') == 2 + n_users

    def test_mtype_empty(self, sr):
        assert sr.get_chat_counts(mtype='sticker')[0] == 'No matching messages'

    def test_n(self, sr):
        assert sr.get_chat_counts(n=3)[0].count('\n') == 2 + 3

    def test_start_out_of_bounds(self, sr):
        assert sr.get_chat_counts(start='2023')[0] == 'No matching messages'

    def test_start_valid(self, sr):
        assert sr.get_chat_counts(start='2020')[0].count('\n') == 2 + n_users

    def test_end_out_of_bounds(self, sr):
        assert sr.get_chat_counts(end='2019')[0] == 'No matching messages'

    def test_end_valid(self, sr):
        assert sr.get_chat_counts(end='2025')[0].count('\n') == 2 + n_users


class TestChatECDF:
    def test_basic(self, sr):
        assert isinstance(sr.get_chat_ecdf()[1], BytesIO)

    def test_lquery(self, sr):
        assert sr.get_chat_ecdf(lquery='dogdfskjweadsf')[0] == 'No matching messages'

    def test_mtype_valid(self, sr):
        assert isinstance(sr.get_chat_ecdf(mtype='text')[1], BytesIO)

    def test_mtype_empty(self, sr):
        assert sr.get_chat_ecdf(mtype='sticker')[0] == 'No matching messages'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_chat_ecdf(start='2023')[0] == 'No matching messages'

    def test_start_valid(self, sr):
        assert isinstance(sr.get_chat_ecdf(start='2020')[1], BytesIO)

    def test_end_out_of_bounds(self, sr):
        assert sr.get_chat_ecdf(end='2019')[0] == 'No matching messages'

    def test_end_valid(self, sr):
        assert isinstance(sr.get_chat_ecdf(end='2025')[1], BytesIO)

    def test_log(self, sr):
        assert isinstance(sr.get_chat_ecdf(log=True)[1], BytesIO)


class TestHours:
    def test_basic(self, sr):
        assert isinstance(sr.get_counts_by_hour()[1], BytesIO)

    def test_user(self, sr):
        assert isinstance(sr.get_counts_by_hour(user=(0, user_table[0]['username']))[1], BytesIO)

    def test_lquery(self, sr):
        assert sr.get_counts_by_hour(lquery='dogsadfadsdfs')[0] == 'No matching messages'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_counts_by_hour(start='2023')[0] == 'No matching messages'

    def test_start_valid(self, sr):
        assert isinstance(sr.get_counts_by_hour(start='2020')[1], BytesIO)

    def test_end_out_of_bounds(self, sr):
        assert sr.get_counts_by_hour(end='2019')[0] == 'No matching messages'

    def test_end_valid(self, sr):
        assert isinstance(sr.get_counts_by_hour(end='2025')[1], BytesIO)


class TestDays:
    def test_basic(self, sr):
        assert isinstance(sr.get_counts_by_day()[1], BytesIO)

    def test_user(self, sr):
        assert isinstance(sr.get_counts_by_day(user=(0, user_table[0]['username']))[1], BytesIO)

    def test_lquery(self, sr):
        assert sr.get_counts_by_day(lquery='dogasdfdfs')[0] == 'No matching messages'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_counts_by_day(start='2023')[0] == 'No matching messages'

    def test_start_valid(self, sr):
        assert isinstance(sr.get_counts_by_day(start='2020')[1], BytesIO)

    def test_end_out_of_bounds(self, sr):
        assert sr.get_counts_by_day(end='2019')[0] == 'No matching messages'

    def test_end_valid(self, sr):
        assert isinstance(sr.get_counts_by_day(end='2025')[1], BytesIO)


class TestWeek:
    def test_basic(self, sr):
        assert isinstance(sr.get_week_by_hourday()[1], BytesIO)

    def test_user(self, sr):
        assert isinstance(sr.get_week_by_hourday(user=(0, user_table[0]['username']))[1], BytesIO)

    def test_lquery(self, sr):
        assert sr.get_week_by_hourday(lquery='dogasdfdfs')[0] == 'No matching messages'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_week_by_hourday(start='2023')[0] == 'No matching messages'

    def test_start_valid(self, sr):
        assert isinstance(sr.get_week_by_hourday(start='2020')[1], BytesIO)

    def test_end_out_of_bounds(self, sr):
        assert sr.get_week_by_hourday(end='2019')[0] == 'No matching messages'

    def test_end_valid(self, sr):
        assert isinstance(sr.get_week_by_hourday(end='2025')[1], BytesIO)


class TestHistory:
    def test_basic(self, sr):
        assert isinstance(sr.get_message_history()[1], BytesIO)

    def test_user(self, sr):
        assert isinstance(sr.get_message_history(user=(0, user_table[0]['username']))[1], BytesIO)

    def test_lquery(self, sr):
        assert sr.get_message_history(lquery='dogasdfdfs')[0] == 'No matching messages'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_message_history(start='2023')[0] == 'No matching messages'

    def test_start_valid(self, sr):
        assert isinstance(sr.get_message_history(start='2020')[1], BytesIO)

    def test_end_out_of_bounds(self, sr):
        assert sr.get_message_history(end='2019')[0] == 'No matching messages'

    def test_end_valid(self, sr):
        assert isinstance(sr.get_message_history(end='2025')[1], BytesIO)

    def test_averages(self, sr):
        assert isinstance(sr.get_message_history(averages=50)[1], BytesIO)


class TestTitleHistory:
    def test_basic(self, sr):
        assert isinstance(sr.get_title_history()[1], BytesIO)

    def test_duration(self, sr):
        assert isinstance(sr.get_title_history(duration=True)[1], BytesIO)

    def test_start_out_of_bounds(self, sr):
        assert sr.get_title_history(start='2023')[0] == "No chat titles in range"

    def test_start_valid(self, sr):
        assert isinstance(sr.get_title_history(start='2020')[1], BytesIO)

    def test_end_out_of_bounds(self, sr):
        assert sr.get_title_history(end='2019')[0] == "No chat titles in range"

    def test_end_valid(self, sr):
        assert isinstance(sr.get_title_history(end='2025')[1], BytesIO)


class TestUserSummary:
    def test_basic(self, sr):
        sr.get_user_summary(user=(0, user_table[0]['username']))

    def test_user_out_of_bounds(self, sr):
        assert sr.get_user_summary(user=(len(user_table), user_table[0]['username']))[0] == 'No data for user'


class TestUserCorrelation:
    def test_basic(self, sr):
        assert sr.get_user_correlation(user=(0, user_table[0]['username']))[0]

    def test_start_out_of_bounds(self, sr):
        assert sr.get_user_correlation(
            start='2023', user=(0, user_table[0]['username']))[0] == 'No messages in range'

    def test_start_valid(self, sr):
        assert sr.get_user_correlation(
            start='2019', user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_end_out_of_bounds(self, sr):
        assert sr.get_user_correlation(
            end='2019', user=(0, user_table[0]['username']))[0] == 'No messages in range'

    def test_end_valid(self, sr):
        assert sr.get_user_correlation(
            end='2025', user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_agg_false(self, sr):
        assert sr.get_user_correlation(
            agg=False, user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_c_spearman(self, sr):
        assert sr.get_user_correlation(
            c_type='spearman', user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_n(self, sr):
        assert sr.get_user_correlation(n=10, user=(0, user_table[0]['username']))[
                   0] != 'No messages in range'

    def test_thresh_valid(self, sr):
        assert sr.get_user_correlation(thresh=0.1, user=(0, user_table[0]['username']))[
                   0] != 'No messages in range'

    def test_thresh_invalid(self, sr):
        with pytest.raises(HelpException):
            sr.get_user_correlation(thresh=1.2, user=(0, user_table[0]['username']))


class TestDeltas:
    def test_basic(self, sr):
        assert 'Sorry' not in sr.get_message_deltas(
            user=(0, user_table[0]['username']))[0]

    def test_lquery(self, sr):
        assert 'Sorry' in sr.get_message_deltas(
            lquery='dogsdfsdsdfs', user=(0, user_table[0]['username']))[0]

    def test_start_out_of_bounds(self, sr):
        assert 'Sorry' in sr.get_message_deltas(
            start='2023', user=(0, user_table[0]['username']))[0]

    def test_start_valid(self, sr):
        assert 'Sorry' not in sr.get_message_deltas(
            start='2019', user=(0, user_table[0]['username']))[0]

    def test_end_out_of_bounds(self, sr):
        assert 'Sorry' in sr.get_message_deltas(
            end='2019', user=(0, user_table[0]['username']))[0]

    def test_end_valid(self, sr):
        assert 'Sorry' not in sr.get_message_deltas(
            end='2025', user=(0, user_table[0]['username']))[0]

    def test_n(self, sr):
        assert sr.get_message_deltas(n=4, user=(0, user_table[0]['username']))[0].count('\n') == 2 + 4

    def test_thresh_valid(self, sr):
        assert 'Sorry' not in sr.get_message_deltas(
            thresh=30, user=(0, user_table[0]['username']))[0]

    def test_thresh_invalid(self, sr):
        assert 'Sorry' in sr.get_message_deltas(
            thresh=3000, user=(0, user_table[0]['username']))[0]


class TestTypeStats:
    def test_basic(self, sr):
        assert sr.get_type_stats(
            user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_type_stats(
            start='2023', user=(0, user_table[0]['username']))[0] == 'No messages in range'

    def test_start_valid(self, sr):
        assert sr.get_type_stats(
            start='2019', user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_end_out_of_bounds(self, sr):
        assert sr.get_type_stats(
            end='2019', user=(0, user_table[0]['username']))[0] == 'No messages in range'

    def test_end_valid(self, sr):
        assert sr.get_type_stats(
            end='2025', user=(0, user_table[0]['username']))[0] != 'No messages in range'


class TestWordStats:
    def test_basic(self, sr):
        assert sr.get_word_stats(
            user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_n(self, sr):
        assert sr.get_word_stats(n=6,
                                 user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_limit(self, sr):
        assert sr.get_word_stats(limit=4,
                                 user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_word_stats(
            start='2023', user=(0, user_table[0]['username']))[0] == 'No messages in range'

    def test_start_valid(self, sr):
        assert sr.get_word_stats(
            start='2019', user=(0, user_table[0]['username']))[0] != 'No messages in range'

    def test_end_out_of_bounds(self, sr):
        assert sr.get_word_stats(
            end='2019', user=(0, user_table[0]['username']))[0] == 'No messages in range'

    def test_end_valid(self, sr):
        assert sr.get_word_stats(
            end='2025', user=(0, user_table[0]['username']))[0] != 'No messages in range'


class TestRandom:
    def test_basic(self, sr):
        assert sr.get_random_message(
            user=(0, user_table[0]['username']))[0] != 'No matching messages'

    def test_lquery(self, sr):
        assert sr.get_random_message(lquery='sadflkjdsflkj',
                                 user=(0, user_table[0]['username']))[0] == 'No matching messages'

    def test_start_out_of_bounds(self, sr):
        assert sr.get_random_message(
            start='2023', user=(0, user_table[0]['username']))[0] == 'No matching messages'

    def test_start_valid(self, sr):
        assert sr.get_random_message(
            start='2019', user=(0, user_table[0]['username']))[0] != 'No matching messages'

    def test_end_out_of_bounds(self, sr):
        assert sr.get_random_message(
            end='2019', user=(0, user_table[0]['username']))[0] == 'No matching messages'

    def test_end_valid(self, sr):
        assert sr.get_random_message(
            end='2025', user=(0, user_table[0]['username']))[0] != 'No matching messages'

