# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.prompt_utils import create_base_prompt, text_trigger
from pedro.utils.text_utils import adjust_pedro_casing


async def default(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        opinions: UserOpinions,
        llm: LLM,
) -> None:
    await opinions.adjust_mood(message)

    if text_trigger(message=message):
        prompt = create_base_prompt(message, history, opinions)

        response = await adjust_pedro_casing(
            await llm.generate_text(prompt)
        )

        history.add_message(response, chat_id=message.chat.id, is_pedro=True)

        await telegram.send_message(
            message_text=response,
            chat_id=message.chat.id,
            reply_to=message.message_id,
        )
