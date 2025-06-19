# Internal
import random

# Project
from pedro.brain.constants.constants import SWEAR_WORDS
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.feedback import sending_action
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.data_structures.telegram_message import Message
from pedro.utils.text_utils import adjust_pedro_casing


async def complain_swearword_trigger(message: Message) -> bool:
    # 5% chance to trigger the reaction when a swear word is detected
    if not message.text:
        return False

    swear_word_detected = any(
        block_word in message.text.lower() for block_word in SWEAR_WORDS
    )

    return swear_word_detected and random.random() < 0.05


async def complain_swearword_reaction(
    message: Message,
    history: ChatHistory,
    telegram: Telegram,
    opinions: UserOpinions,
    llm: LLM,
) -> None:
    is_triggered = await complain_swearword_trigger(message)

    if not is_triggered:
        return

    prompts = {
        'critique': 'Critique o linguajar dessa mensagem:',
        'critique_reformule': 'Critique o linguagem dessa mensagem e reformule para uma forma apropriada:',
        'continue': 'Continue a mensagem e critique o linguajar:'
    }

    # Randomly select a prompt from the dictionary
    prompt_key = random.choice(list(prompts.keys()))
    selected_prompt = prompts[prompt_key]

    with sending_action(chat_id=message.chat.id, telegram=telegram):
        prompt = f"{selected_prompt} {message.text}"
        mock_message = await llm.generate_text(
            prompt=prompt,
            model="gpt-3.5-turbo-instruct",
            temperature=1.0,
        )

        mock_message = await adjust_pedro_casing(mock_message)

        await history.add_message(mock_message, chat_id=message.chat.id, is_pedro=True)

        await telegram.send_message(
            message_text=mock_message,
            chat_id=message.chat.id,
            reply_to=message.message_id,
            sleep_time=1 + (round(random.random()) * 4)
        )
