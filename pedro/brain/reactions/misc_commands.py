# Internal
import json
import logging
import random

# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.text_utils import create_username

logger = logging.getLogger(__name__)

# Constants
MAX_MOOD = 10


async def misc_commands_reaction(
        message: Message,
        history: ChatHistory,
        telegram: Telegram,
        opinions: UserOpinions,
        llm: LLM,
) -> None:
    if message.text:
        if message.text.startswith("/me"):
            await handle_me_command(message, telegram, opinions)
        elif message.text.startswith('/del') and message.reply_to_message:
            await handle_del_command(message, telegram, llm)
        elif message.text.startswith('/data'):
            await handle_data_command(telegram)
        elif message.text.startswith('/puto'):
            await handle_puto_command(message, telegram, opinions, llm)


async def handle_me_command(
    message: Message,
    telegram: Telegram,
    opinions: UserOpinions,
) -> None:
    """Handle the /me command, showing user ID, chat ID, and mood score."""
    user_mood = 0

    username = create_username(message.from_.first_name, message.from_.username)
    for user_opinion in opinions.get_all_user_opinions():
        user_name = create_username(user_opinion.first_name, user_opinion.username)
        if username == user_name:
            user_mood = round(user_opinion.my_mood_with_him, 2)

    await telegram.send_message(
        message_text=f"*ID:* `{message.from_.id}`\n"
                     f"*Chat ID:* `{message.chat.id}`\n"
                     f"*Meu ódio por você:* `{user_mood}`",
        chat_id=message.chat.id,
        reply_to=message.message_id,
        parse_mode="Markdown"
    )


async def handle_del_command(
    message: Message,
    telegram: Telegram,
    llm: LLM,
) -> None:
    """Handle the /del command, which deletes messages or responds with criticism."""
    if message.reply_to_message.from_.username is None:
        message.reply_to_message.from_.username = ""

    if (
            message.reply_to_message.from_.id == message.from_.id
            or "pedroleblon" in message.reply_to_message.from_.username
            or message.reply_to_message.from_.is_bot
    ):
        await telegram.delete_message(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id
        )

        await telegram.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id
        )

        # Log the deletion
        logger.info(f"{message.from_.first_name},{message.text},{message.reply_to_message.text}")
    else:
        with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
            from_username = create_username(
                first_name=message.from_.first_name,
                username=message.from_.username
            )
            reply_username = create_username(
                first_name=message.reply_to_message.from_.first_name,
                username=message.reply_to_message.from_.username
            )

            response = await llm.generate_text(
                f'critique duramente o '
                f'{from_username} '
                f'por ter tentado deletar a mensagem "{message.reply_to_message.text}" enviada por'
                f" {reply_username}. 'diga que pretende baní-lo do {message.chat.title}.\n\n"
                f"pedro:",
                temperature=1,
                model="gpt-3.5-turbo-instruct"
            )

            await telegram.send_message(
                message_text=response.upper(),
                chat_id=message.chat.id,
                reply_to=message.message_id,
            )


async def handle_data_command(
    telegram: Telegram,
) -> None:
    """Handle the /data command, sending database content to a specific chat."""
    with open("database/pedro_database.json", "r", encoding="utf-8") as f:
        db_content = json.load(f)

    await telegram.send_document(
        document=json.dumps(db_content, indent=4).encode("utf-8"),
        chat_id=8375482,
        caption="DB"
    )


async def handle_puto_command(
    message: Message,
    telegram: Telegram,
    opinions: UserOpinions,
    llm: LLM,
) -> None:
    username = create_username(message.from_.first_name, message.from_.username)

    # Get user mood
    user_mood = 0
    for user_opinion in opinions.get_all_user_opinions():
        user_name = create_username(user_opinion.first_name, user_opinion.username)
        if username == user_name:
            user_mood = round(user_opinion.my_mood_with_him, 2)

    if user_mood < 0:
        user_mood = 0

    with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
        prompt = f"considere que você é o pedro.\nem uma escala de 0 a {MAX_MOOD}, " \
                 f"onde:\n" \
                 f"0 = extremamente contente, melhores amigos\n" \
                 f"1 = contente" \
                 f"\n...\n" \
                 f"5 = neutro" \
                 f"\n...\n" \
                 f"{MAX_MOOD - 1} = puto" \
                 f"\n{MAX_MOOD} = extremamente puto:\n"

        if message.text.startswith('/putos'):
            persons = ""
            for user_opinion in opinions.get_all_user_opinions():
                mood = user_opinion.my_mood_with_him
                if mood > 3:
                    user_name = create_username(user_opinion.first_name, user_opinion.username)
                    persons += f"{user_name.split(' ')[0]}: {int(mood)}\n"

            if persons:
                prompt += f"temos as seguintes pessoas seguidas da escala do quanto você está puto com elas:\n\n{persons}\n\n" \
                          f"descreva de maneira como você, pedro, se sente com cada uma dessas pessoas, sem dizer o valor da escala. " \
                          f"reclame grosseiramente com aqueles que te deixaram puto, lembrando de alguma situação que essa pessoa fez com você.\npedro:"
            else:
                prompt = "diga que não está irritado com ninguém.\npedro:"
        else:
            prompt += f"temos o seguinte valor:\n\n{user_mood}\n\nentão, dentro da escala, " \
                 f"diga para o {username} o quanto você " \
                 f"está contente ou puto com ele. sem dizer exatamente os valores e nem revelar a escala." \
                 f"\n{'dê um exemplo de como você se sente com isso.' if round(random.random()) else 'faça uma curta poesia sobre isso.'}\n\n" \
                 f"\npedro:"

        response = await llm.generate_text(
            prompt,
            temperature=1,
            model="gpt-3.5-turbo-instruct"
        )

        await telegram.send_message(
            message_text=response.lower(),
            chat_id=message.chat.id,
            reply_to=message.message_id,
        )
