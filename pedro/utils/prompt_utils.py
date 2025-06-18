from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.datetime_manager import DatetimeManager
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.text_utils import create_username


def create_base_prompt(message: Message, memory: ChatHistory, opinions: UserOpinions, total_messages=10) -> str:
    datetime = DatetimeManager()

    chat_history = memory.get_friendly_last_messages(chat_id=message.chat.id, limit=total_messages)

    users_opinions = opinions.get_users_by_text_match(chat_history)

    text = message.caption if message.caption else message.text

    if text:
        base_prompt = f"{opinions.get_mood_level_prompt(message.from_.id)}\n\nFingindo ser o Pedro, responda a mensagem '{text}' no final da conversa.\n\n"
    else:
        base_prompt = f"{opinions.get_mood_level_prompt(message.from_.id)}\n\nFingindo ser o Pedro, responda sobre imagem no final da conversa.\n\n"

    opinions_text = ""

    for user_opinion in users_opinions:
        if user_opinion.opinions:
            user_opinions_text = "\n".join(user_opinion.opinions)
            user_display_name = create_username(user_opinion.first_name, user_opinion.username)
            opinions_text += f"Opiniões de Pedro sobre {user_display_name}: \n{user_opinions_text}\n\n"

    return base_prompt + opinions_text + chat_history + f"\n{datetime.get_current_time_str()} - UserID [0] - Pedro (pedroleblonbot): "


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
