# Internal
import asyncio
import random
from unidecode import unidecode

# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_data_manager import UserDataManager
from pedro.data_structures.telegram_message import Message


async def political_trigger(message: Message) -> bool:
    if not message.text or not message.from_.username:
        return False

    political_words = ["governo", "lula", "faz o l", "china", "bostil", "lixo de pa", "imposto", "bolsonaro", "xii", "trump", "milei"]
    target_users = ["decaptor", "nands93"]

    return (any(word in message.text.lower() for word in political_words) and 
            any(user in message.from_.username for user in target_users))


async def congratulations_trigger(message: Message) -> bool:
    if not message.text:
        return False

    congrats_words = ["parabens", "muito bom", "otimo", "excelente"]
    return any(word in unidecode(message.text.lower()) for word in congrats_words)


async def lgbt_trigger(message: Message) -> bool:
    if not message.text:
        return False

    lgbt_words = [" viado", "bicha", "gay"]
    return (any(word in unidecode(message.text.lower()) for word in lgbt_words) and 
            "enviado" not in message.text.lower())


async def emoji_reactions(
    message: Message,
    history: ChatHistory,
    telegram: Telegram,
    user_data: UserDataManager,
    llm: LLM,
) -> None:
    if await political_trigger(message):
        asyncio.create_task(
            telegram.set_message_reaction(
                message_id=message.message_id,
                chat_id=message.chat.id,
                reaction=random.choice(["💩", "🤡", "🤪"]),
            )
        )

    if await congratulations_trigger(message):
        asyncio.create_task(
            telegram.set_message_reaction(
                message_id=message.message_id,
                chat_id=message.chat.id,
                reaction=random.choice(["🎉", "👏", "🏆", "🍾", "❤", "💯"]),
            )
        )

    if await lgbt_trigger(message):
        asyncio.create_task(
            telegram.set_message_reaction(
                message_id=message.message_id,
                chat_id=message.chat.id,
                reaction=random.choice(["💅", "🦄", "🌭", "👀", "🌚"]),
            )
        )
