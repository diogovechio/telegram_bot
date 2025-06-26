# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_data_manager import UserDataManager
from pedro.brain.reactions.fact_check import fact_check
from pedro.data_structures.images import MessageImage
from pedro.data_structures.telegram_message import Message
from pedro.utils.prompt_utils import image_trigger, create_basic_prompt
from pedro.utils.text_utils import adjust_pedro_casing


async def images_reaction(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        user_data: UserDataManager,
        llm: LLM,
) -> None:
    if message.photo or message.document:
        image = await telegram.image_downloader(message)
        if image and message.from_.username in ["nands93", "decaptor"]:
            with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
                political_prompt = ("Analise esta imagem e verifique se ela contém conteúdo de cunho político ou "
                                    "menciona algum político. "
                                    "Responda apenas com 'SIM', 'PROVÁVEL' ou 'NÃO'. "
                                    "Não elabore ou explique sua resposta.")

                response = await llm.generate_text(political_prompt, model="gpt-4.1-mini", image=image)

                if "SIM" in response.upper() or "PROV" in response.upper():
                    await fact_check(
                        message, history, telegram, user_data, llm
                    )

        elif image and image_trigger(message):
            with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
                prompt = await create_basic_prompt(
                message=message, memory=history, user_data=user_data, total_messages=3, telegram=telegram, llm=llm)

                response = await adjust_pedro_casing(
                    await llm.generate_text(prompt, model="gpt-4.1-mini", image=image)
                )

                await history.add_message(response, chat_id=message.chat.id, is_pedro=True)

                await telegram.send_message(
                    message_text=response,
                    chat_id=message.chat.id,
                    reply_to=message.message_id,
                )
    return None
