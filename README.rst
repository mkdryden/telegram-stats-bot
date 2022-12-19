==================
telegram-stats-bot
==================

.. image:: https://img.shields.io/pypi/v/telegram-stats-bot?style=flat-square
   :target: https://pypi.org/project/telegram-stats-bot/
   :alt: PyPi Package Version

.. image:: https://img.shields.io/pypi/pyversions/telegram-stats-bot?style=flat-square
   :target: https://pypi.org/project/telegram-stats-bot/
   :alt: Supported Python versions

.. image:: https://img.shields.io/github/commit-activity/m/mkdryden/telegram-stats-bot?style=flat-square
   :target: https://github.com/mkdryden/telegram-stats-bot
   :alt: GitHub Commit Activity

.. image:: https://img.shields.io/pypi/l/telegram-stats-bot?style=flat-square
   :target: https://www.gnu.org/licenses/gpl-3.0-or-later.html
   :alt: LGPLv3 License


Telegram-stats-bot is a simple bot that lives in your Telegram group, logging messages to a Postgresql database and
serving statistical tables and plots to users as Telegram messages.

.. image:: examples/chat_example.png
    :alt: Bot conversation example

-----------------
Table of contents
-----------------

- `Introduction`_

- `Basic Requirements`_

- `Installation`_

- `Docker`_

- `Setup`_

- `Importing Data`_

- `Fetching Stats`_

  - `counts`_

  - `hours`_

  - `days`_

  - `week`_

  - `history`_

  - `titles`_

  - `user`_

  - `corr`_

  - `delta`_

  - `types`_

  - `words`_

  - `random`_

- `License`_

------------
Introduction
------------

This software is intended to be run on a server, handling updates for a bot user with a single bot per channel
(multi-channel support could be added at some point if there is interest), using the excellent
`Python-telegram-bot <https://github.com/python-telegram-bot/python-telegram-bot>`_ library.

The bot is still in active development but at the moment, it features:

- Message logging to Postgresql database with optional JSON file backup

- Statistics output for users in group as Telegram messages, with optional filtering by date or limiting to the querying
  user.
  Some statistics are more useful than others, but they are mainly intended to be fun for users to play with.

  - Tables:

    - Most active users

    - A user's message time correlation with other users

    - A user's median message time difference with other users

  - Plots:

    - Message activity by hour of day

    - Message activity by day of week

    - Message activity over the week by hour and day

    - Message activity history

------------------
Basic Requirements
------------------

- Python 3.8+

- A Telegram bot token with privacy mode disabled (needed to log messages)

  - See `here <https://core.telegram.org/bots#6-botfather>`_ for details

- Postgresql (Tested with 12.3, but there shouldn't be anything that won't work with 9.4 or up)

  - This can be on a different system than telegram-stats-bot and requires either table creation permissions on a
    database or database can be pre-initialized following the setup in ``db.py``

------------
Installation
------------

The easiest way to install or upgrade is with pip:

.. code:: shell

    $ pip install telegram-stats-bot --upgrade

This works directly from the git repository as well:

.. code:: shell

    $ pip install --upgrade git+https://github.com/mkdryden/telegram-stats-bot

Or you can install an entire venv for development using `poetry <https://python-poetry.org/>`_:

.. code:: shell

    $ git clone https://github.com/mkdryden/telegram-stats-bot.git
    $ cd telegram-stats-bot
    $ poetry install

------
Docker
------

A Docker image is available under ``mkdryden/telegram-stats-bot`` and a sample ``docker-compose.yml`` is in the root of the repository including database setup.
Be sure to set the ``TZ``, ``BOT_TOKEN``, and ``CHAT_ID`` environment variable appropriately in your ``docker-run`` command or the ``docker-compose.yml`` file.

-----
Setup
-----
Once installed, you can run the bot by calling the ``main`` module with a few required arguments:

.. code:: shell

    $ python -m telegram_stats_bot.main BOT_TOKEN CHAT_ID POSTGRESQL_URL

- ``BOT_TOKEN``: Your bot's token e.g., ``110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw``

- ``CHAT_ID``: The chat id to monitor (will be a large integer, possibly negative, if unknown, set to 0 and see below)

- ``POSTGRESQL_URL``: Connection information in the form: ``postgresql://USERNAME:PASSWORD@ADDRESS/DB_NAME``

  - if DB_NAME exists, there must not be tables called ``messages_utc``, ``user_events``, or ``user_names``
    with incorrect columns

Two optional arguments exist as well:

- ``json-path``: Specifying a path here will log messages to json files in addition to the database.
  If only a prefix is specified, they will be saved under that prefix in your platform's preferred app data directory.
  This was mostly for development purposes and is not necessary in normal use.

- ``tz``: Specify a tz database time zone string here (e.g., ``America/New_York``) to return statistics queries in this time zone.
  (Defaults to ``Etc./UTC``)

A complete command might look like:

.. code:: shell

    $ python -m telegram_stats_bot.main --tz="America/Toronto" "110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw" "postgresql://telegram:CoolPassword@localhost/telegram_bot"

On startup, the bot will attempt to create the database and tables, if they do not already exist.
If you do not know the chat's id and have set it to 0 as mentioned above, you can send the ``/chatid`` command inside
the group, and the bot will reply with it, then restart the bot with the id.
If you have forgotten to disable privacy mode, an error will be logged in the terminal.

The bot will now log all messages in the group, but will only respond to users who have sent a message that has been
logged previously (and this list is only updated once an hour, so if you're impatient, you can restart the bot after
you've sent a message to trigger the update).
You can see if messages are being logged correctly by reviewing the terminal output.
You should see a line like ``2020-06-04 02:08:39,212 - __main__ - INFO - 8``, whenever a message is logged.

--------------
Importing Data
--------------
Data can be imported from JSON dumps from the desktop client.
Hit the three dot button from inside the desired group and select "Export chat history".
Make sure you select JSON as the output format.
You can also limit the date, as desired.
The database will be updated and existing messages will remain, so you can use this feature to fill in gaps when the bot was not running.

To import data, simply call:

.. code:: shell

    $ python -m telegram_stats_bot.json_dump_parser "/some/path/to/dump.json" "postgresql://telegram:CoolPassword@localhost/telegram_bot" --tz="America/Toronto"

Where the first argument is the path to the json dump, the second is the db connection string, as above, and the optional `tz` argument should be the time zone of the system used to dump the json.

This can be run without stopping a running bot, though it also attempts to set the user id to user name mapping, so will add an extra entry to every user in the dump (this currently only affects the user stats related to user name changes).
Before you run this, make sure your db string is correct or you might accidentally mess up other databases on the same server.

--------------
Fetching Stats
--------------
To fetch stats, simply message the bot, either inside the group being logged, or in a direct message, using the
``/stats`` command.
``/stats`` with no arguments prints the table of most active users and other statistics are available through various
subcommands.
All commands are documented and the built in help can be displayed with ``/stats -h`` or ``stats <subcommand> -h``.

Most commands have optional arguments that change the behaviour of the output.
Nearly all have:

- ``-start`` and ``-end`` followed by a timestamp (e.g., 2019, 2019-01, 2019-01-01, "2019-01-01 14:21") specify the
  range of data to fetch, otherwise all available data will be used.
  Either or both options can be given.

- ``-lquery`` followed by a lexical query (using Postgres'
  `tsquery syntax <https://www.postgresql.org/docs/12/datatype-textsearch.html#DATATYPE-TSQUERY>`_)
  limits results to matching messages.

- ``-me`` calculates statistics for the user sending the command, rather than all chat users.

Sample outputs of each available subcommand follow.

counts
------
``/stats counts`` returns a list of the most active users in the group.

.. code::

                User  Total Messages  Percent
          @ACoolUser           42150      7.0
          @NumberOne           37370      6.2
   @WinstonChurchill           32668      5.4
            @AAAAAAA           32134      5.4
  @WhereAreMyManners           30481      5.1
  @TheWorstOfTheBest           28705      4.8

hours
-----
``/stats hours`` returns a plot of message frequency for the hours of the day.

.. image:: examples/hours.png
   :alt: Example of hours plot

days
----
``/stats days`` returns a plot of message frequency for the days of the week.

.. image:: examples/days.png
   :alt: Example of days plot

week
----
``/stats week`` returns a plot of total messages over the data period by day of week and hour of day.

.. image:: examples/week.png
   :alt: Example of week plot

history
-------
``/stats history`` returns a plot of messages versus date.

.. image:: examples/history.png
   :alt: Example of history plot

titles
------
``/stats titles`` returns a plot of group titles over time.

.. image:: examples/titles.png
   :alt: Example of title history plot

user
----
``/stats user`` returns basic statistics for the user.

.. code-block::

    Messages sent: 16711
    Average messages per day: 12.31
    First message was 1357.22 days ago.
    Usernames on record: 3
    Average username lifetime: 452.41 days

    joined on 2017-10-01 16:11:08-04:00

corr
----
``/stats corr`` returns a list of users with the highest and lowest message time correlations with the requesting user.

.. code::

    User Correlations for @TheManWhoWasThursday
    HIGHEST CORRELATION:
    @MyGoodFriend         0.335
    @Rawr                 0.302
    @MangesUnePoutine     0.284
    @GreenBlood           0.251
    @TooMuchVacuum        0.235

    LOWEST CORRELATION:
    @Shiny                0.146
    @BlueDog              0.142
    @CoolCat              0.122
    @EatMe                0.116
    @JustPassingBy        0.106

delta
-----
``/stats delta`` returns a list of users with the shortest differences in message times with the requesting user.

.. code::

    Median message delays for @KingLeer and:
    @PolyamorousPasta     00:03:23
    @AggressiveArgon      00:04:43
    @AdjectiveNoun        00:08:27
    @SuperSalad           00:09:05
    @ABoredProgrammer     00:09:06

types
-----
``/stats types`` returns a table of messages by type, comparing the requesting user with the full group.

.. code::

 Messages by type, @AUser vs group:
       type  Group Count  Group Percent  User Count  User Percent
       text     528813.0           88.3     13929.0          83.4
    sticker      34621.0            5.8      1226.0           7.3
      photo      25995.0            4.3      1208.0           7.2
  animation       6983.0            1.2       274.0           1.6
      video       1325.0            0.2        48.0           0.3
      voice        475.0            0.1         2.0           0.0
   location        252.0            0.0         2.0           0.0
 video_note         84.0            0.0         1.0           0.0
      audio         62.0            0.0         1.0           0.0
       poll         29.0            0.0         1.0           0.0
   document          1.0            0.0         1.0           0.0
      Total     598640.0          100.0     16693.0         100.0

words
-----
``/stats words`` returns a table of the most commonly used lexemes

.. code::

 Most frequently used lexemes:
     Lexeme  Messages  Uses
       like      1265  1334
       well       753   765
     actual       628   645
       make       600   619
       yeah       609   609
       mean       544   553
      thing       473   490
     realli       472   482
     though       467   470
      peopl       415   445
      think       425   433
       know       403   409
       need       396   408
       time       371   389
       want       354   371
      would       345   366
       much       345   357
    probabl       348   356
       even       331   338
      stuff       318   332

random
------
``/stats random`` prints a random message from the database.

----------
The Future
----------
Telegram-stats-bot is a work in progress.
New stats will be added, but no guarantees that the database structure will stay constant if Telegram's message
structure changes or I need to change something to make a new statistic work.

=======
License
=======
Telegram-stats-bot is free software:
You can redistribute it and/or modify it under the terms of the
`GNU General Public License v3.0 or later <https://www.gnu.org/licenses/gpl-3.0.html>`_.
Derivative works must also be redistributed under the GPL v3 or later.
