# Internal
import asyncio
import logging
from asyncio import AbstractEventLoop
from datetime import datetime
import json
import typing as T

from pedro.brain.modules.agenda import AgendaManager
# External

# Project
from pedro.__version__ import __version__
from pedro.data_structures.bot_config import BotConfig
from pedro.data_structures.daily_flags import DailyFlags
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.reactions.messages_handler import messages_handler
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.database import Database
from pedro.brain.modules.user_data_manager import UserDataManager
from pedro.brain.modules.scheduler import Scheduler

logging.basicConfig(level=logging.INFO)


class TelegramBot:
    def __init__(
            self,
            bot_config_file: str,
            secrets_file: str,
            debug_mode=False
    ):
        self.version = __version__
        self.allowed_list = []
        self.debug_mode = debug_mode

        self.config: T.Optional[BotConfig] = None
        self.config_file = bot_config_file
        self.secrets_file = secrets_file

        self.datetime_now = datetime.now()

        self.llm: T.Optional[LLM] = None
        self.telegram: T.Optional[Telegram] = None

        self.database: T.Optional[Database] = None
        self.user_data: T.Optional[UserDataManager] = None
        self.chat_history: T.Optional[ChatHistory] = None
        self.scheduler = None
        self.agenda: AgendaManager | None = None

        self.lock = True

        self.daily_flags = DailyFlags(
            swearword_complain_today=False,
            swearword_random_reaction_today=False,
            random_talk_today=False
        )

        self.loop: T.Optional[AbstractEventLoop] = None

    async def run(self) -> None:
        try:
            self.loop = asyncio.get_running_loop()

            await self.load_config_params()

            await asyncio.gather(
                self._unlocker(),
                self._message_handler()
            )

        except Exception as exc:
            logging.exception(exc)

            await asyncio.sleep(60)

            await self.run()

    async def load_config_params(self) -> None:
        logging.info(f'Pedro Bot v{__version__} - Loading params')

        with open(self.config_file, encoding='utf8') as config_file:
            with open(self.secrets_file) as secret_file:
                bot_config = json.loads(config_file.read())

                bot_config.update(
                    json.loads(secret_file.read())
                )

                self.config: BotConfig = BotConfig(**bot_config)

                self.telegram = Telegram(self.config.secrets.bot_token)
                self.agenda = AgendaManager(self.telegram)
                self.llm = LLM(self.config.secrets.openai_key)
                self.database = Database("database/pedro_database.json")
                self.chat_history = ChatHistory(telegram=self.telegram, llm=self.llm)
                self.user_data = UserDataManager(self.database, self.llm, telegram=self.telegram, chat_history=self.chat_history)

                # Process historical messages for all users
                self.loop.create_task(self.user_data.get_opinion_by_historical_messages())

                # Initialize and start the scheduler to run process_historical_messages every day at 9 AM,
                # database backup every day at 21:00, and reset daily flags at 5 AM
                self.scheduler = Scheduler(self.user_data, self.telegram, self.daily_flags)
                self.scheduler.start()

                self.allowed_list = [value.id for value in self.config.allowed_ids]

        logging.info('Loading finished')

    async def _message_handler(self) -> None:
        while True:
            try:
                await asyncio.sleep(0.01)

                async for message in self.telegram.get_new_message():
                    message = message.message

                    if message and message.chat:
                        await self.chat_history.add_message(message, chat_id=message.chat.id)
                        self.user_data.add_user_if_not_exists(message)

                        if not self.lock:
                            self.loop.create_task(
                                messages_handler(
                                    message=message,
                                    telegram=self.telegram,
                                    history=self.chat_history,
                                    user_data=self.user_data,
                                    allowed_list=self.allowed_list,
                                    agenda=self.agenda,
                                    llm=self.llm,
                                    daily_flags=self.daily_flags,
                                    config=self.config,
                                )
                            )

            except Exception as exc:
                logging.exception(exc)
                await asyncio.sleep(15)

    async def _unlocker(self) -> None:
        await asyncio.sleep(3)

        self.lock = False
