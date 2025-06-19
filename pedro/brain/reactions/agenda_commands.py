# Internal
import re
import math
import uuid
from datetime import datetime

# Project
from pedro.brain.modules.chat_history import ChatHistory
from pedro.brain.modules.datetime_manager import DatetimeManager
from pedro.brain.modules.telegram import Telegram
from pedro.brain.modules.user_opinion_manager import UserOpinions
from pedro.brain.modules.llm import LLM
from pedro.brain.modules.agenda import AgendaManager
from pedro.data_structures.telegram_message import Message

# Constants for date patterns
ANNUAL_DATE_PATTERN = r"^\d{2}/\d{2}$"  # DD/MM
ONCE_DATE_PATTERN = r"^\d{2}/\d{2}/\d{4}$"  # DD/MM/YYYY

async def trigger_new(message: Message) -> bool:
    return message.text and message.text.lower().startswith("/agendar")


async def trigger_list(message: Message) -> bool:
    return message.text and message.text.lower().startswith("/agenda")


async def trigger_new_birthday(message: Message) -> bool:
    return message.text and message.text.lower().startswith("/aniversario")


async def delete_trigger(message: Message) -> bool:
    return message.text and message.text.lower().startswith("/delete")


async def agenda_commands_reaction(
    message: Message,
    history: ChatHistory,
    telegram: Telegram,
    opinions: UserOpinions,
    agenda_manager: AgendaManager,
    llm: LLM,
) -> None:
    """
    Handle agenda-related commands.

    Args:
        message: The message to process
        history: Chat history manager
        telegram: Telegram API wrapper
        opinions: User opinions manager
        llm: Language model manager
        :param agenda_manager:
    """
    now = DatetimeManager().now()

    # Check which command was triggered
    new_data = await trigger_new(message)
    list_data = await trigger_list(message)
    new_birthday = await trigger_new_birthday(message)
    delete = await delete_trigger(message)

    if not (new_data or list_data or new_birthday or delete):
        return

    # Split the message text into words
    message_split = message.text.split()

    # Handle /agendar command
    if new_data:
        frequency = None
        celebration = None

        # Determine the frequency based on the date format
        if len(message_split) > 1 and re.fullmatch(ANNUAL_DATE_PATTERN, message_split[-1]):
            frequency = 'annual'
        elif len(message_split) > 1 and len(message_split[-1]) == 2 and message_split[-1].isdigit() and 0 < int(message_split[-1]) < 32:
            frequency = 'monthly'
        elif len(message_split) > 1 and re.fullmatch(ONCE_DATE_PATTERN, message_split[-1]):
            frequency = 'once'

        # If the command format is invalid, show usage examples
        if len(message_split) < 3 or not frequency:
            await telegram.send_message(
                message_text=f"Exemplo pra agendar:\n"
                             f"\n<b>Exemplo 1 (anual): </b>/agendar hoje é dia de 29/12"
                             f"\n<b>Exemplo 2 (uma vez): </b>/agendar me lembra de sei la 29/12/2023"
                             f"\n<b>Exemplo 3 (mensal): </b>/agendar me lembra disso 05 "
                             f"(obs.: 31 será sempre considerado o último dia do mês)",
                chat_id=message.chat.id,
                reply_to=message.message_id,
                parse_mode="HTML"
            )
        else:
            # Parse the date based on the frequency
            if frequency == "annual":
                celebration = datetime.strptime(f"{message_split[-1]}/{now.year}", "%d/%m/%Y")
            elif frequency == "once":
                celebration = datetime.strptime(f"{message_split[-1]}", "%d/%m/%Y")
            elif frequency == "monthly":
                celebration = datetime.strptime(f"{message_split[-1]}/{now.month}/{now.year}", "%d/%m/%Y")

            # Extract the message text
            text = message.text.replace(message_split[-1], '').replace(message_split[0], '').strip()

            # Add the agenda item to the database
            if celebration and frequency:
                agenda_manager.add_agenda_item(
                    frequency=frequency,
                    created_by=message.from_.id,
                    celebrate_at=celebration,
                    for_chat=message.chat.id,
                    message=text,
                    anniversary=""
                )

                # Send a confirmation message
                await telegram.send_message(
                    message_text=f"<b>{text}</b>\n{message_split[-1]}\nadicionado na agenda",
                    chat_id=message.chat.id,
                    reply_to=message.message_id,
                    parse_mode="HTML"
                )

    # Handle /agenda command
    elif list_data:
        # Get all agenda items for the current chat
        agenda_items = agenda_manager.get_agenda_items_for_chat(message.chat.id)

        if not agenda_items:
            await telegram.send_message(
                message_text="Não há agendamentos para este chat.",
                chat_id=message.chat.id,
                reply_to=message.message_id,
                parse_mode="HTML"
            )
            return

        # Format the agenda items for display
        agenda_texts = []
        for item in agenda_items:
            date_text = f"{item.celebrate_at.day}"
            if item.frequency != 'monthly':
                date_text += f"/{item.celebrate_at.month}"
            if item.frequency == 'once':
                date_text += f"/{item.celebrate_at.year}"

            reminder_text = item.message if not item.anniversary else f"Aniversário de {item.anniversary.replace('@', '@ ')}"

            agenda_texts.append(
                f"<b>ID: {item.id}</b>\n"
                f"<b>Data:</b> {date_text}\n"
                f"<b>Lembrete:</b> {reminder_text}\n"
                f"<b>Frequência:</b> {item.frequency}\n"
                f"<b>{message.from_.first_name} autorizado a deletar:</b> {item.created_by == message.from_.id}"
            )

        # Split the agenda items into multiple messages if needed
        message_len = 8
        agendas = []
        last_idx = 0
        messages_count = math.ceil(len(agenda_texts) / message_len)

        for i in range(messages_count):
            agendas.append('\n\n'.join(agenda_texts[last_idx:last_idx + message_len]))
            last_idx += message_len

        # Send the messages
        for i, entry in enumerate(agendas):
            await telegram.send_message(
                message_text=f"<b>Agendamentos do chat {message.chat.title if message.chat.title else message.chat.username}</b> - {i + 1}/{len(agendas)}\n\n{entry}",
                chat_id=message.chat.id,
                parse_mode="HTML"
            )

    # Handle /aniversario command
    elif new_birthday:
        # Check if the command format is valid
        if len(message_split) < 3 or not re.fullmatch(ANNUAL_DATE_PATTERN, message_split[-1]):
            await telegram.send_message(
                message_text=f"exemplo pra agendar:\n\n/aniversario @thommazk 29/12",
                chat_id=message.chat.id,
                reply_to=message.message_id,
                parse_mode="HTML"
            )
        else:
            # Parse the date
            celebration = datetime.strptime(f"{message_split[-1]}/{now.year}", "%d/%m/%Y")

            # Extract the anniversary name
            anniversary = message.text.lower().replace(message_split[-1], '').replace(message_split[0], '').strip()

            # Add the anniversary to the database
            agenda_item = agenda_manager.add_agenda_item(
                frequency="annual",
                created_by=message.from_.id,
                celebrate_at=celebration,
                for_chat=message.chat.id,
                message="",
                anniversary=anniversary
            )

            # Send a confirmation message
            await telegram.send_message(
                message_text=f"aniversário de {anniversary} no dia {message_split[-1]} adicionado na agenda",
                chat_id=message.chat.id,
                reply_to=message.message_id,
                parse_mode="HTML"
            )

    elif delete:
        msg_id = message.text.split(' ')

        if len(msg_id) != 2:
            await telegram.send_message(
                message_text=f"Para deletar entrada da agenda:\n/delete id",
                chat_id=message.chat.id,
                reply_to=message.message_id,
                parse_mode="HTML"
            )
        else:
            item_id = msg_id[-1]
            item = agenda_manager.get_agenda_item_by_id(item_id)

            if item and item.created_by == message.from_.id:
                if agenda_manager.delete_agenda_item(item_id):
                    await telegram.send_message(
                        message_text=f"{item_id} deletado da agenda",
                        chat_id=message.chat.id,
                        reply_to=message.message_id,
                        parse_mode="HTML"
                    )
                else:
                    await telegram.send_message(
                        message_text=f"Erro ao deletar {item_id}. Tente novamente.",
                        chat_id=message.chat.id,
                        reply_to=message.message_id,
                        parse_mode="HTML"
                    )
            else:
                await telegram.send_message(
                    message_text=f"Não achei {item_id}... manda /agenda e copia o id direito "
                                 f"ou vê se você tem permissão pra deletar",
                    chat_id=message.chat.id,
                    reply_to=message.message_id,
                    parse_mode="HTML"
                )
