# -*- coding: utf-8 -*-

# Copyright (C) 2013-2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging
import datetime
import sys

from xivo_stat import queue
from xivo_stat import agent
from xivo_dao import stat_queue_periodic_dao
from xivo_dao import stat_agent_periodic_dao
from xivo_dao import stat_call_on_queue_dao
from xivo_dao import queue_log_dao
from xivo_dao import stat_queue_dao
from xivo_dao import stat_agent_dao
from xivo_dao.helpers.db_utils import session_scope

logger = logging.getLogger(__name__)

_ERASE_TIME_WHEN_STARTING = datetime.timedelta(hours=8)
DELTA_1HOUR = datetime.timedelta(hours=1)


def hour_start(t):
    return datetime.datetime(t.year,
                             t.month,
                             t.day,
                             t.hour)


def end_of_previous_hour(t):
    return hour_start(t) - datetime.timedelta(microseconds=1)


def get_start_time(dao_sess):
    try:
        start = hour_start(stat_queue_periodic_dao.get_most_recent_time(dao_sess))
    except LookupError:
        try:
            start = hour_start(queue_log_dao.get_first_time(dao_sess))
        except LookupError:
            raise RuntimeError('No data to generate stats from')
    return start - _ERASE_TIME_WHEN_STARTING


def update_db(end_date, start_date=None):
    if start_date is None:
        try:
            with session_scope() as dao_sess:
                start = get_start_time(dao_sess)
        except RuntimeError:
            return
    else:
        start = datetime.datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S')

    end = datetime.datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S')

    logger.info('Filling cache into DB')
    logger.info('Start Time: %s, End time: %s', start, end)
    try:
        with session_scope() as dao_sess:
            insert_missing_queues(dao_sess, start, end)
            insert_missing_agents(dao_sess)
            dao_sess.flush()

            queue.remove_between(dao_sess, start, end)
            agent.remove_after_start(dao_sess, start)
            queue.fill_simple_calls(dao_sess, start, end)
            dao_sess.flush()

            agent.insert_periodic_stat(dao_sess, start, end)

            for period_start in queue_log_dao.hours_with_calls(dao_sess, start, end):
                period_end = period_start + datetime.timedelta(hours=1) - datetime.timedelta(microseconds=1)
                queue.fill_calls(dao_sess, period_start, period_end)
                queue.insert_periodic_stat(dao_sess, period_start, period_end)
    except:
        logger.exception("error while updating database")
        sys.exit(1)


def clean_db():
    with session_scope() as dao_sess:
        stat_call_on_queue_dao.clean_table(dao_sess)
        stat_agent_periodic_dao.clean_table(dao_sess)
        stat_queue_periodic_dao.clean_table(dao_sess)
        stat_agent_dao.clean_table(dao_sess)
        stat_queue_dao.clean_table(dao_sess)


def insert_missing_agents(dao_sess):
    logger.info('Inserting missing agents...')
    stat_agent_dao.insert_missing_agents(dao_sess)


def insert_missing_queues(dao_sess, start, end):
    logger.info('Inserting missing queues...')
    queue_names = queue_log_dao.get_queue_names_in_range(dao_sess, start, end)
    stat_queue_dao.insert_if_missing(dao_sess, queue_names)
