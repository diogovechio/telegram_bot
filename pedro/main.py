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
from pedro.data_structures.bot_config import BotConfig
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.reactions.messages_handler import messages_handler
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.database import Database
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.brain.modules.scheduler import Scheduler

logging.basicConfig(level=logging.INFO)


class TelegramBot:
    def __init__(
            self,
            bot_config_file: str,
            secrets_file: str,
            debug_mode=False
    ):
        self.allowed_list = []
        self.debug_mode = debug_mode

        self.config: T.Optional[BotConfig] = None
        self.config_file = bot_config_file
        self.secrets_file = secrets_file

        self.datetime_now = datetime.now()

        self.llm: T.Optional[LLM] = None
        self.telegram: T.Optional[Telegram] = None

        self.database: T.Optional[Database] = None
        self.user_opinion_manager: T.Optional[UserOpinions] = None
        self.chat_history: T.Optional[ChatHistory] = None

        self.agenda: AgendaManager | None = None

        self.lock = True

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
        logging.info('Loading params')

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
                self.user_opinion_manager = UserOpinions(self.database, self.llm, chat_history=self.chat_history)

                # Process historical messages for all users
                self.loop.create_task(self.user_opinion_manager.get_opinion_by_historical_messages())

                # Initialize and start the scheduler to run process_historical_messages every day at 9 AM
                self.scheduler = Scheduler(self.user_opinion_manager)
                self.scheduler.start()

                self.allowed_list = [value.id for value in self.config.allowed_ids]

        logging.info('Loading finished')

    async def _message_handler(self) -> None:
        while True:
            try:
                await asyncio.sleep(0.5)

                async for message in self.telegram.get_new_message():
                    message = message.message

                    if message and message.chat:
                        await self.chat_history.add_message(message, chat_id=message.chat.id)
                        self.user_opinion_manager.add_user_if_not_exists(message)

                        if not self.lock:
                            self.loop.create_task(
                                messages_handler(
                                    message=message,
                                    telegram=self.telegram,
                                    history=self.chat_history,
                                    opinions=self.user_opinion_manager,
                                    allowed_list=self.allowed_list,
                                    agenda=self.agenda,
                                    llm=self.llm,
                                )
                            )

            except Exception as exc:
                logging.exception(exc)
                await asyncio.sleep(15)

    async def _unlocker(self) -> None:
        await asyncio.sleep(3)

        self.lock = False
