=========
Changelog
=========
All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

----------
Unreleased
----------
Changed
-------
- Upgraded python-telegram-bot to version 20
- Reply to edited messages
- Updated to SQLAlchemy 2.0
- Updated to pandas 2.1
- Updated other dependencies
- Separate SQL code from db_init function
- Update to psycopg 3.0

Fixed
-----
- Date selection for word statistics was broken
- Incorrect datatype for column in user_events table

----------
`0.7.0`_ - 2023-01-14
----------
Fixed
-----
- Sticker pack names save correctly now
- Explicitly add psycopg2-binary as dependency because sqlalchemy extra doesn't seem to work anymore
- Try to map user ids to names during json dump import. (#17)

Added
-----
- Add script to import data from desktop client json dumps
- Add ECDF plot for message counts by user with ``/stats count-dist``

-------------
`0.6.4`_ - 2022-02-27
-------------
Changed
-------
- Bumped python-telegram-bot to version 13.11 (#9)

-------------
`0.6.3`_ - 2022-01-13
-------------
Changed
-------
- Titles plot uses seconds resolution with -duration option

Fixed
-----
- Fix database creation code for immutable SQLAlchemy 1.4 URLs
- Titles plot considers time zone correctly for current time. (Prevents negative bars in titles plot with -duration option)

----------
`0.6.2`_ - 2021-11-11
----------
Changed
-----
- Switched build backend to poetry-core so that PEP 517 builds don't need full poetry install

----------
`0.6.1`_ - 2021-11-07
----------
Changed
-----
- Bumped pillow version to 8.3.2 for security reasons

----------
`0.6.0`_ - 2021-06-20
----------
Added
-----
- Time zone support with ``--tz`` option
- stats: user statistics

---------------------
`0.5.0`_ - 2021-06-11
---------------------
Added
-----
- Allow limiting counts by message type
- stats: Added words statistic

Fixed
-----
- Remove @ from random message to avoid pinging users
- Allow quotes in lquery parameters
- Zero-fill days without data for history
- Display error message if counts query empty
- Use random dollarsign quoting to pass lquery parameter

---------------------
`0.4.0`_ - 2021-06-06
---------------------
Added
-----
- Read version from bot
- stats: add lexical query to several stats

Removed
-------
- Python 3.7 support removed

Changed
-------
- Updated to python-telegram-bot 13.6

---------------------
`0.3.1`_ - 2020-12-31
---------------------
Security
--------
- Bump crypography requirement to address security vulnerability

---------------------
`0.3.0`_ - 2020-10-06
---------------------
Fixed
-----
- Correctly escape all reserved markdown characters and markdown links

Added
-----
- Print a random message from the log ``/stats random``
- Allow sorting title history plot by duration

---------------------
`0.2.0`_ - 2020-06-16
---------------------

Added
-----
- Message type statistics ``/stats types``
- Group title history plot ``/stats titles``

Fixed
-----
- Example images were missing in pypi distributions
- Git install instructions were incorrect
- Example images now .png instead of .jpg

----------------------
`0.1.1`_ - 2020-06-05
----------------------
- Initial release

.. _Unreleased: https://github.com/mkdryden/telegram-stats-bot/compare/v0.7.0...HEAD
.. _0.1.1: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.1.1
.. _0.2.0: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.2.0
.. _0.3.0: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.3.0
.. _0.3.1: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.3.1
.. _0.4.0: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.4.0
.. _0.5.0: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.5.0
.. _0.6.0: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.6.0
.. _0.6.1: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.6.1
.. _0.6.2: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.6.2
.. _0.6.3: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.6.3
.. _0.7.0: https://github.com/mkdryden/telegram-stats-bot/releases/tag/v0.7.0
