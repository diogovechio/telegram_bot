from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.datetime_manager import DatetimeManager
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.text_utils import create_username
import logging

logger = logging.getLogger(__name__)


async def process_reply_message(message: Message, memory: ChatHistory) -> str:
    if not message.reply_to_message:
        return ""

    reply = message.reply_to_message
    sender_name = create_username(reply.from_.first_name, reply.from_.username) if reply.from_ else "Unknown"

    if reply.photo:
        image_description = await memory.process_reply_photo(reply)
        return f"... (em resposta à imagem enviada por {sender_name}: {image_description})"
    else:
        reply_text = reply.text or ""
        return f"... (em resposta a mensagem enviada por {sender_name}: [[{reply_text}]] )"


async def create_basic_prompt(message: Message, memory: ChatHistory, opinions: UserOpinions, total_messages=15) -> str:
    datetime = DatetimeManager()

    chat_history = memory.get_friendly_last_messages(chat_id=message.chat.id, limit=total_messages)

    users_opinions = opinions.get_users_by_text_match(chat_history)

    text = message.caption if message.caption else message.text

    reply_text = ""
    if message.reply_to_message:
        reply_text = await process_reply_message(message, memory)

    if text:
        base_prompt = (f"{opinions.get_mood_level_prompt(message.from_.id)}\n\nVocê é o Pedro, "
                       f"responda a mensagem '{text}' enviada "
                       f"por {create_username(message.from_.first_name, message.from_.username)}.\n\n")
    else:
        base_prompt = (f"{opinions.get_mood_level_prompt(message.from_.id)}\n\nVocê é o Pedro,"
                       f" responda sobre imagem '{text}'enviada "
                       f"por {create_username(message.from_.first_name, message.from_.username)}.\n\n")

    opinions_text = ""

    for user_opinion in users_opinions:
        if user_opinion.opinions:
            user_opinions_text = "\n".join(user_opinion.opinions)
            user_display_name = create_username(user_opinion.first_name, user_opinion.username)
            opinions_text += f"Opiniões de Pedro sobre {user_display_name}: \n{user_opinions_text}\n\n"

    return base_prompt + opinions_text + chat_history + reply_text + f"\n{datetime.get_current_time_str()} - UserID [0] - Pedro (pedroleblonbot): "


def text_trigger(message: Message) -> bool:
    return (
            message.text and
            (message.text.lower().startswith("pedro") or message.text.lower().replace("?", "").strip().endswith(
                "pedro"))
    ) or (
            message.reply_to_message and "pedro" in message.reply_to_message.from_.username
    )

def image_trigger(message: Message) -> bool:
    return (
            message.caption and
            (message.caption.lower().startswith("pedro") or message.caption.lower().replace("?", "").strip().endswith(
                "pedro"))
    )
