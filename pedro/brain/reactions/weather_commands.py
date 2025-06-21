# Internal
import logging

# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_data_manager import UserDataManager
from pedro.data_structures.telegram_message import Message
from pedro.data_structures.bot_config import BotConfig
from pedro.utils.weather_utils import get_forecast

logger = logging.getLogger(__name__)


async def weather_commands_reaction(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        user_data: UserDataManager,
        llm: LLM,
        config: BotConfig,
) -> None:
    """Handle weather-related commands."""
    if message.text and (message.text.startswith("/previsao") or message.text.startswith("/prev")):
        await handle_previsao_command(message, telegram, config, user_data)


async def handle_previsao_command(
    message: Message,
    telegram: Telegram,
    config: BotConfig,
    user_data: UserDataManager = None,
) -> None:
    """Handle the /previsao command, showing weather forecast for the specified location."""
    # Extract the location from the command
    command_parts = message.text.split(" ", 1)

    if len(command_parts) > 1:
        location = command_parts[1].strip()

        # Store the location in the user's opinion if opinions is provided
        if user_data and message.from_:
            user_opinion = user_data.add_user_if_not_exists(message)
            user_opinion.last_weather_location = location
            user_data.database.update(
                user_data.table_name,
                {"last_weather_location": location},
                {"user_id": message.from_.id}
            )

        with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
            # Get the weather forecast
            forecast = await get_forecast(config, location, 7)  # Default to 7 days forecast

            # Send the forecast
            await telegram.send_message(
                message_text=forecast,
                chat_id=message.chat.id,
                reply_to=message.message_id,
            )
    else:
        # No location specified, try to use the last requested location
        location = None
        if user_data and message.from_:
            user_opinion = user_data.get_user_opinion(message.from_.id)
            if user_opinion and user_opinion.last_weather_location:
                location = user_opinion.last_weather_location

        if location:
            with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
                # Get the weather forecast using the last requested location
                forecast = await get_forecast(config, location, 7)  # Default to 7 days forecast

                # Send the forecast
                await telegram.send_message(
                    message_text=forecast,
                    chat_id=message.chat.id,
                    reply_to=message.message_id,
                )
        else:
            # No location specified and no last requested location
            await telegram.send_message(
                message_text="Por favor, especifique um local após o comando. Exemplo: /previsao Rio de Janeiro",
                chat_id=message.chat.id,
                reply_to=message.message_id,
            )
