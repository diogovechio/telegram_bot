# Internal
import random

# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.text_utils import adjust_pedro_casing


async def fact_check_trigger(message: Message) -> bool:
    return message.text and (
        message.text.lower().startswith("/refute") or 
        message.text.lower().startswith("/fact") or
        message.text.lower().startswith("/check")
    )


async def fact_check_reaction(
    message: Message,
    history: ChatHistory,
    telegram: Telegram,
    opinions: UserOpinions,
    llm: LLM,
) -> None:
    is_fact_check = await fact_check_trigger(message)

    if not is_fact_check:
        return

    training_counterpoint = """Como especialista em verificação de fatos e jornalista com 
    uma perspectiva marxista materialista e dialética, examine 'Argumento' a 
    partir de uma perspectiva de defesa da classe trabalhadora. Identifique 
    fatos que se oponham ao Argumento, independentemente de quão desafiadoras 
    ou desconfortáveis os fatos possam ser. Se o 'Argumento' contiver múltiplas 
    posições deconstrua-o em suas partes constituintes e analise cada uma separadamente. 
    Pare - Guarde a 'Análise da resposta' e não me diga nada. Siga - Formule uma 'Resposta' 
    materialista e dialética sucinta da 'Análise da resposta', sem referência à abordagem 
    metodológica utilizada."""

    with sending_action(chat_id=message.chat.id, telegram=telegram, user=message.from_.username):
        if message.reply_to_message and message.reply_to_message.text:
            mentiroso = message.reply_to_message.from_.first_name
            mentiroso_argument = message.reply_to_message.text

            prompt = f"{training_counterpoint} Responda o Argumento de {mentiroso}: '{mentiroso_argument}'"

            reply_to = message.reply_to_message.message_id

            fact_check_text = await llm.generate_text(
                prompt=f"{prompt}",
                temperature=0.6,
            )

            fact_check_text = fact_check_text.lower()

            prompt_fact_checked = f"""Como especialista em verificação de fatos e jornalista 
            com uma perspectiva marxista materialista e dialética, você formulou a 
            seguinte Análise: "{fact_check_text}"; sobre o Argumento do {mentiroso}: "{mentiroso_argument}"; 
            Responda o {mentiroso} de forma sucinta e direta com base na Análise, indo direto ao ponto com 
            foco no contra-argumento, sem mencionar a sua perspectiva ou metodologia."""

            message_text = await llm.generate_text(
                prompt=prompt_fact_checked,
                temperature=0.7,
            )

            message_text = message_text.lower()

            if mentiroso.lower() not in message_text and message.reply_to_message and not message.reply_to_message.from_.is_bot:
                message_text = f"{mentiroso}, {message_text}"

            if random.random() < 0.25:
                message_text = message_text.upper()

            message_text = await adjust_pedro_casing(message_text)

            await history.add_message(message_text, chat_id=message.chat.id, is_pedro=True)

            await telegram.send_message(
                message_text=message_text,
                chat_id=message.chat.id,
                reply_to=reply_to
            )
