# Internal
import asyncio
import json
import logging
from datetime import datetime, timezone

# External
import schedule

# Project
from pedro.brain.modules.user_data_manager import UserDataManager
from pedro.brain.modules.datetime_manager import DatetimeManager
from pedro.brain.modules.telegram import Telegram
from pedro.data_structures.daily_flags import DailyFlags


def _convert_hour_if_needed(time_str: str) -> str:
    local_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().total_seconds() / 3600

    hours, minutes = map(int, time_str.split(':'))
    if abs(local_tz_offset + 3) < 0.1:
        logging.info(f"No timezone conversion needed, system already in GMT-3 (offset: {local_tz_offset})")
    else:
        logging.info(f"Converting from GMT-3 to UTC (system timezone offset: {local_tz_offset})")
        hours = (hours + 3) % 24

    return f"{hours:02d}:{minutes:02d}"


def call_async_function(func):
    asyncio.get_running_loop().create_task(func())


class Scheduler:
    def __init__(self, user_opinions: UserDataManager, telegram: Telegram, daily_flags: DailyFlags | None = None):
        self.user_opinions = user_opinions
        self.datetime_manager = DatetimeManager()
        self.telegram = telegram
        self.daily_flags = daily_flags
        self.running = False

    async def _run_process_historical_messages(self):
        logging.info(f"Running scheduled task: process_historical_messages at {self.datetime_manager.now()}")
        await self.user_opinions.get_opinion_by_historical_messages()

    async def _run_database_backup(self):
        logging.info(f"Running scheduled task: database_backup at {self.datetime_manager.now()}")
        with open("database/pedro_database.json", "r", encoding="utf-8") as f:
            db_content = json.load(f)

        await self.telegram.send_document(
            document=json.dumps(db_content, indent=4).encode("utf-8"),
            chat_id=8375482,
            caption="Daily DB Backup"
        )

    async def _reset_daily_flags(self):
        """Reset all daily flags to False at 5 AM."""
        if self.daily_flags:
            logging.info(f"Running scheduled task: reset_daily_flags at {self.datetime_manager.now()}")
            self.daily_flags.swearword_complain_today = False
            self.daily_flags.swearword_random_reaction_today = False
            self.daily_flags.random_talk_today = False
            self.daily_flags.random_tease_message = False
            logging.info("All daily flags have been reset to False")

    async def _reset_random_tease_message(self):
        if self.daily_flags:
            self.daily_flags.random_tease_message = False

    async def run_scheduler(self):
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(1)

    def start(self):
        if self.running:
            logging.warning("Scheduler is already running")
            return

        schedule.every().day.at(
            _convert_hour_if_needed("09:00")).do(
                call_async_function,
                self._run_process_historical_messages
        )

        schedule.every().day.at(
            _convert_hour_if_needed("15:00")).do(
                call_async_function,
                self._run_process_historical_messages
        )

        schedule.every().day.at(
            _convert_hour_if_needed("22:00")).do(
                call_async_function,
                self._run_process_historical_messages
        )

        schedule.every().day.at(
            _convert_hour_if_needed("21:00")).do(
                call_async_function,
                self._run_database_backup
        )

        schedule.every().day.at(
            _convert_hour_if_needed("19:00")).do(
                call_async_function,
                self._reset_daily_flags
        )

        schedule.every(3).hours.do(
            call_async_function,
            self._reset_random_tease_message
        )

        self.running = True

        asyncio.create_task(self.run_scheduler())

        logging.info("Scheduler started")
