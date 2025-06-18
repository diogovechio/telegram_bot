# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.datetime_manager import DatetimeManager
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.text_utils import adjust_pedro_casing


async def default(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        opinions: UserOpinions,
        llm: LLM,
) -> None:
    await opinions.adjust_mood(message)
    _ = history.get_messages(message.chat.id, days_limit=5)
    if trigger(message=message):
        user_opinion = opinions.get_user_opinion(user_id=message.from_.id)
        prompt = create_prompt(message, history, opinions)

        response = await adjust_pedro_casing(
            await llm.generate_text(prompt)
        )

        history.add_message(response, chat_id=message.chat.id, is_pedro=True)

        await telegram.send_message(
            message_text=response,
            chat_id=message.chat.id,
            reply_to=message.message_id,
        )


def create_prompt(message: Message, memory: ChatHistory, opinions: UserOpinions) -> str:
    datetime = DatetimeManager()

    base_prompt = f"{opinions.get_mood_level_prompt(message.from_.id)}\n\nFingindo ser o Pedro, responda a mensagem '{message.text}' no final da conversa.\n\n"

    chat_history = memory.get_friendly_last_messages(chat_id=message.chat.id, limit=10)
    return base_prompt + chat_history + f"\n{datetime.get_current_time_str()} - UserID [0] - Pedro (pedroleblonbot): "


def trigger(message: Message) -> bool:
    return (
            message.text and
            (message.text.startswith("pedro") or message.text.replace("?", "").strip().endswith(
                "pedro"))
    ) or (
            message.reply_to_message and "pedro" in message.reply_to_message.from_.username
    )
