# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.prompt_utils import create_basic_prompt, text_trigger
from pedro.utils.text_utils import adjust_pedro_casing


async def default(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        opinions: UserOpinions,
        llm: LLM,
) -> None:
    if text_trigger(message=message):
        await opinions.adjust_mood(message)

        with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
            web_search = any(word in message.text.lower() for word in ["cotação", "fonte", "pesquis", "google", "busque", "notícia", "noticia"])
            model = "gpt-4.1-mini" if web_search else "gpt-4.1-nano"

            prompt = await create_basic_prompt(
                message, history,
                opinions=None if web_search else opinions,
                total_messages=3 if web_search else 15
            )

            response = await adjust_pedro_casing(
                await llm.generate_text(prompt, model=model, web_search=web_search)
            )

            await history.add_message(response, chat_id=message.chat.id, is_pedro=True)

            await telegram.send_message(
                message_text=response,
                chat_id=message.chat.id,
                reply_to=message.message_id,
            )
