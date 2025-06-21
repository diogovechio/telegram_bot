# Project
import random

from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_data_manager import UserDataManager
from pedro.data_structures.daily_flags import DailyFlags
from pedro.data_structures.telegram_message import Message
from pedro.utils.prompt_utils import create_basic_prompt, text_trigger, check_web_search
from pedro.utils.text_utils import adjust_pedro_casing


async def default(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        user_data: UserDataManager,
        llm: LLM,
        daily_flags: DailyFlags,
) -> None:
    if text_trigger(message=message, daily_flags=daily_flags):
        await user_data.adjust_mood(message)

        with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
            web_search = check_web_search(message)
            model = "gpt-4.1-mini" if web_search else "gpt-4.1-nano"

            prompt = await create_basic_prompt(
                message, history,
                user_data=None if web_search else user_data,
                total_messages=3 if web_search else 10,
                telegram=telegram
            )

            response = await adjust_pedro_casing(
                await llm.generate_text(prompt, model=model, web_search=web_search)
            )

            await history.add_message(response, chat_id=message.chat.id, is_pedro=True)

            await telegram.send_message(
                message_text=response,
                chat_id=message.chat.id,
                reply_to=message.message_id,
                disable_web_page_preview=web_search
            )
