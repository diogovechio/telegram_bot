# Internal
import asyncio

# External

# Project
from pedro.brain.reactions.default_pedro import default
from pedro.data_structures.telegram_message import Message
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.user_opinion_manager import UserOpinions


async def messages_handler(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        opinions: UserOpinions,
        llm: LLM,
        allowed_list: list,
) -> None:
    if message.chat.id in allowed_list:
        await asyncio.gather(
            default(message, history, telegram, opinions, llm),
        )
