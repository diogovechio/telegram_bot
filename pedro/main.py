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
    """
    Main Telegram bot class that handles configuration, initialization and message processing.
    
    This class sets up the bot with the provided configuration, manages connections to various
    services like LLM, database, and handles incoming Telegram messages.

    Attributes:
        bot_config_file (str): Path to the bot configuration file
        secrets_file (str): Path to the secrets configuration file  
        debug_mode (bool): Whether to run the bot in debug mode
    """

    def __init__(
            self,
            bot_config_file: str,
            secrets_file: str,
            debug_mode=False
    ):
        """
        Initialize the TelegramBot with configuration files and debug settings.

        Args:
            bot_config_file (str): Path to the bot configuration file
            secrets_file (str): Path to the secrets file containing sensitive data
            debug_mode (bool, optional): Enable debug mode. Defaults to False.
        """
        self.version = __version__
        self.allowed_list = []
        self.debug_mode = debug_mode

        self.config: BotConfig | None = None
        self.config_file = bot_config_file
        self.secrets_file = secrets_file

        self.llm: LLM | None = None
        self.telegram: Telegram | None = None
        self.database: Database | None = None
        self.user_data: UserDataManager | None = None
        self.chat_history: ChatHistory | None = None
        self.agenda: AgendaManager | None = None
        self.scheduler: Scheduler | None = None

        self.lock = True

        self.daily_flags = DailyFlags(
            swearword_complain_today=False,
            swearword_random_reaction_today=False,
            random_talk_today=False,
            random_tease_message=False
        )

        self.loop: T.Optional[AbstractEventLoop] = None

    async def run(self) -> None:
        """
        Start the bot and begin processing messages.
        
        This method initializes configuration parameters and starts the main bot tasks.
        Will attempt to reconnect after 60 seconds if an error occurs.
        """
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
        """
        Load and initialize all configuration parameters and services.
        
        This includes loading bot and secret configurations, initializing database connection,
        telegram client, LLM, chat history manager and scheduler.
        """
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
                self.user_data = UserDataManager(
                    database=self.database,
                    llm=self.llm,
                    telegram=self.telegram,
                    chat_history=self.chat_history,
                )

                self.loop.create_task(self.user_data.get_opinion_by_historical_messages())

                self.scheduler = Scheduler(self.user_data, self.telegram, self.daily_flags)
                self.scheduler.start()

                self.allowed_list = [value.id for value in self.config.allowed_ids]

        logging.info('Loading finished')

    async def _message_handler(self) -> None:
        """
        Main message processing loop that handles incoming Telegram messages.
        
        Continuously monitors for new messages, adds them to chat history and 
        processes them through the message handler if the bot is unlocked.
        """
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
        """
        Unlocks the bot after a short delay to avoid reacting with messages sent before the initialization.
        
        Waits 3 seconds before unlocking the bot to accept and process messages.
        """
        await asyncio.sleep(3)

        self.lock = False
