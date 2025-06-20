import random
import asyncio

from pedro.brain.constants.constants import POLITICAL_OPINIONS, POLITICAL_WORDS
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.datetime_manager import DatetimeManager
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.daily_flags import DailyFlags
from pedro.data_structures.telegram_message import Message
from pedro.utils.text_utils import create_username
import logging

logger = logging.getLogger(__name__)


async def send_telegram_log(
        telegram: Telegram,
        message_text: str,
        parse_mode: str = "HTML",
        message=None
) -> None:
    log_chat_id = -1002051541243
    if message:
        try:
            chat_name = message.chat.title if hasattr(message.chat, 'title') and message.chat.title else str(message.chat.id)
            user_name = create_username(message.from_.first_name, message.from_.username) if message.from_ else "Unknown"
            log_message = f"Prompt gerado para chat: {chat_name}\nUsuário: {user_name}"
            await telegram.send_message(message_text=log_message, chat_id=log_chat_id, parse_mode="HTML")
            logger.info(f"Prompt sent to log chat {log_chat_id}")
        except Exception as e:
            logger.error(f"Failed to send prompt to log chat: {e}")

    # Maximum message length
    max_message_length = 1500

    # If message is shorter than the maximum length, send it directly
    if len(message_text) <= max_message_length:
        await telegram.send_message(
            message_text=message_text,
            chat_id=log_chat_id,
            parse_mode=parse_mode,
        )
        return

    # Split message into chunks of maximum length
    chunks = []
    for i in range(0, len(message_text), max_message_length):
        chunks.append(message_text[i:i + max_message_length])

    # Send each chunk sequentially
    for i, chunk in enumerate(chunks):
        # Add a prefix to indicate this is part of a multi-part message
        prefix = f"[Parte {i+1}/{len(chunks)}]\n" if len(chunks) > 1 else ""

        await telegram.send_message(
            message_text=prefix + chunk,
            chat_id=log_chat_id,
            parse_mode=parse_mode,
        )


async def process_reply_message(message: Message, memory: ChatHistory) -> str:
    if not message.reply_to_message:
        return ""

    reply = message.reply_to_message
    sender_name = create_username(reply.from_.first_name, reply.from_.username) if reply.from_ else "Unknown"
    sender_name = f"{reply.from_.first_name} - {sender_name}"

    if reply.photo:
        image_description = await memory.process_photo(reply)
        return f" ->> [... {sender_name} havia enviado a imagem: {image_description} ]"
    else:
        reply_text = reply.text or ""
        return f" ->>  [... {sender_name} havia dito anteriormente: [[{reply_text}]] ]"


async def create_basic_prompt(message: Message, memory: ChatHistory, opinions: UserOpinions | None, total_messages=15, telegram: Telegram | None = None) -> str:
    datetime = DatetimeManager()

    chat_history = memory.get_friendly_last_messages(chat_id=message.chat.id, limit=total_messages)

    political_opinions = ""
    if any(political_word.lower() in chat_history.lower() for political_word in POLITICAL_WORDS):
        political_opinions = "\n".join(POLITICAL_OPINIONS)
        political_opinions = f"{political_opinions}\n\n"

    if opinions:
        users_opinions = opinions.get_users_by_text_match(chat_history)

    text = message.caption if message.caption else message.text

    reply_text = ""
    if message.reply_to_message:
        reply_text = await process_reply_message(message, memory)

    if not opinions:
        base_prompt = (f"Você é o Pedro, responda a mensagem '{text}' enviada "
                       f"por {create_username(message.from_.first_name, message.from_.username)}.\n\n")
    elif opinions and text:
        base_prompt = (f"{opinions.get_mood_level_prompt(message.from_.id)}\n\nVocê é o Pedro, "
                       f"responda a mensagem '{text}' enviada "
                       f"por {create_username(message.from_.first_name, message.from_.username)}.\n\n")
    else:
        base_prompt = (f"{opinions.get_mood_level_prompt(message.from_.id)}\n\nVocê é o Pedro,"
                       f" responda sobre imagem '{text}'enviada "
                       f"por {create_username(message.from_.first_name, message.from_.username)}.\n\n")

    opinions_text = ""

    if opinions:
        for user_opinion in users_opinions:
            if user_opinion.opinions:
                user_display_name = create_username(user_opinion.first_name, user_opinion.username)
                user_display_name = f"{user_opinion.first_name} - {user_display_name}"
                user_opinions_text = "\n".join([f"Sobre {user_display_name}: {opinion[:100]}" for opinion in user_opinion.opinions])
                opinions_text += f"### RESPONDA COM BASE NAS INFORMAÇÕES A SEGUIR SE FOR PERGUNTADO SOBRE ***{user_display_name}*** ### \n{user_opinions_text}\n\n"

    prompt = base_prompt + political_opinions + opinions_text + chat_history + reply_text + f"\n{datetime.get_current_time_str()} - Pedro (pedroleblonbot): "

    if telegram:
        asyncio.create_task(send_telegram_log(
            telegram=telegram,
            message_text=prompt,
            message=message
        ))

    return prompt


def text_trigger(message: Message, daily_flags: DailyFlags) -> bool:
    if random.random() < 0.15 and not daily_flags.random_talk_today:
        daily_flags.random_talk_today = True

        return True

    return (
            message.text and
            (message.text.lower().startswith("pedro") or message.text.lower().replace("?", "").strip().endswith(
                "pedro"))
    ) or (
            message.reply_to_message and "pedro" in message.reply_to_message.from_.username and not message.text.startswith("/")
    )

def image_trigger(message: Message) -> bool:
    return (
            message.caption and
            (message.caption.lower().startswith("pedro") or message.caption.lower().replace("?", "").strip().endswith(
                "pedro"))
    )
