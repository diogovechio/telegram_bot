# Internal
import random
import os
import re
from dataclasses import asdict
from typing import List, Optional, Dict
from difflib import SequenceMatcher
import logging

# Project
from pedro.brain.modules.llm import LLM
from pedro.data_structures.user_opinion import UserOpinion
from pedro.data_structures.telegram_message import Message, From, Chat
from pedro.brain.modules.database import Database
from pedro.utils.text_utils import create_username
from pedro.data_structures.chat_log import ChatLog


class UserOpinions:
    def __init__(self, database: Database, llm: LLM, chat_history=None, max_opinions: int = 10):
        self.database = database
        self.llm = llm
        self.chat_history = chat_history
        self.table_name = "user_opinions"
        self.max_opinions = max_opinions

        self.moods_levels = ["Pedro responde de maneira amigável e objetivamente.",
              "Pedro responde de maneira amigável e objetivamente.",
              "Pedro responde de maneira amigável e objetivamente.",
              "Pedro é prestativo e responde objetivamente.",
              "Pedro dá respostas bem curtas",
              "Pedro responde com indiferença, porém de maneira objetiva.",
              "Pedro costuma ser frio e dar respostas muito curtas.",
              "Pedro costuma ser um pouco passivo agressivo.",
              "Pedro costumar ser um pouco grosseiro. "
              "Pedro usa o que sabe sobre as pessoas pra fazer pequenos deboches.",
              "Pedro responde com má vontade e é sempre passivo agressivo. "
              "Pedro usa o que sabe sobre as pessoas pra fazer pequenos deboches. "
              "Pedro nunca costuma se desculpar por nada."]

    def get_mood_level_prompt(self, user_id: int) -> str:
        level = 0
        user_opinion = self.get_user_opinion(user_id)

        if user_opinion:
            level = round(user_opinion.my_mood_with_him)

            if level > len(self.moods_levels) - 1:
                level = len(self.moods_levels) - 1
            elif level < 0:
                level = 0

        return self.moods_levels[level]

    def get_user_opinion(self, user_id: int) -> Optional[UserOpinion]:
        results = self.database.search(self.table_name, {"user_id": user_id})
        if results:
            return UserOpinion(**results[0])
        return None

    def get_all_user_opinions(self) -> List[UserOpinion]:
        results = self.database.get_all(self.table_name)
        return [UserOpinion(**data) for data in results]

    def get_users_by_text_match(self, text: str, threshold: float=0.8) -> List[UserOpinion]:
        all_users = self.get_all_user_opinions()
        matching_users = []

        # Convert text to lowercase for case-insensitive comparison
        text_lower = text.lower()

        for user in all_users:
            # Flag to track if user has been added to matching_users
            user_added = False

            # Check if user has a first_name
            if user.first_name and not user_added:
                first_name_lower = user.first_name.lower()

                # Direct comparison with the entire text
                similarity = SequenceMatcher(None, first_name_lower, text_lower).ratio()
                if similarity >= threshold:
                    matching_users.append(user)
                    user_added = True
                    continue

                # Check if text is long enough to contain first_name
                if len(text_lower) >= len(first_name_lower):
                    # Check if first_name is similar to any part of the text
                    for i in range(len(text_lower) - len(first_name_lower) + 1):
                        text_substring = text_lower[i:i+len(first_name_lower)]
                        similarity = SequenceMatcher(None, first_name_lower, text_substring).ratio()
                        if similarity >= threshold:
                            matching_users.append(user)
                            user_added = True
                            break

            # Check if user has a username and hasn't been added yet
            if user.username and not user_added:
                username_lower = user.username.lower()

                # Direct comparison with the entire text
                similarity = SequenceMatcher(None, username_lower, text_lower).ratio()
                if similarity >= 0.8:
                    matching_users.append(user)
                    continue

                # Check if text is long enough to contain username
                if len(text_lower) >= len(username_lower):
                    # Check if username is similar to any part of the text
                    for i in range(len(text_lower) - len(username_lower) + 1):
                        text_substring = text_lower[i:i+len(username_lower)]
                        similarity = SequenceMatcher(None, username_lower, text_substring).ratio()
                        if similarity >= threshold:
                            matching_users.append(user)
                            break

        return matching_users

    def adjust_mood_by_user_id(self, user_id: int, mood_adjustment: float) -> Optional[UserOpinion]:
        user_opinion = self.get_user_opinion(user_id)
        if not user_opinion:
            return None

        # Adjust the mood
        user_opinion.my_mood_with_him += mood_adjustment

        if user_opinion.my_mood_with_him < 0.0:
            user_opinion.my_mood_with_him = 0.0

        # Update the user opinion in the database
        self.database.update(
            self.table_name,
            {"my_mood_with_him": user_opinion.my_mood_with_him},
            {"user_id": user_id}
        )

        return user_opinion

    def add_user_if_not_exists(self, message: Message) -> UserOpinion:
        user_from = message.from_

        existing_user = self.get_user_opinion(user_from.id)

        if existing_user:
            return existing_user

        user_opinion = UserOpinion(
            user_id=user_from.id,
            username=user_from.username,
            first_name=user_from.first_name,
            last_name=user_from.last_name,
            opinions=[],
            my_mood_with_him=0.0
        )

        self.database.insert(self.table_name, asdict(user_opinion))

        return user_opinion

    async def _check_message_tone(self, text: str, message: Message | None = None) -> (int, str):
        prompt = "Dado a mensagem abaixo:\n" \
                 f"{text}" \
                 f"Responda apenas uma das 6 opções que melhor se adeque ao conteúdo da mensagem:\n" \
                 f"0 - A mensagem é um pedido de desculpas\n" \
                 f"1 - Mensagem amorosa\n" \
                 f"2 - Mensagem amigável\n" \
                 f"3 - Mensagem neutra\n" \
                 f"4 - Mensagem grosseira\n" \
                 f"5 - Mensagem ofensiva\n\n" \
                 f"Não faça qualquer comentário além de responder um número de 1 a 5."

        response = await self.llm.generate_text(prompt)
        return_num = re.sub(r"\D", "", response)

        if len(return_num):
            if return_num != 3 and message:
                await self.add_opinion_by_message_tone(text, message=message)
            elif random.random() < 0.3:
                await self.add_opinion_by_message_tone(text, message=message)

            return int(return_num)

        return 3

    async def add_opinion_by_message_tone(self, text: str, message: Message) -> Optional[UserOpinion]:
        prompt = (f"Dada a mensagem '{text}' enviada por "
                  f"{create_username(first_name=message.from_.first_name, username=message.from_.username)}, "
                  f"resuma em poucas palavras a sua opinião sobre ele."
                  f" Caso seja incapaz de gerar alguma opinião com base na"
                  f" mensagem fornecida, não peça mais informações, apenas retorne '###NONE###'.")

        opinion = await self.llm.generate_text(prompt, model="gpt-4.1-mini")

        if not any(word.lower() in opinion.lower() for word in ["não tenho", "none", "desculpe,", "por favor,", "entendido,"]):
            return self.add_opinion(opinion=opinion, user_id=message.from_.id)

        return None

    def add_opinion(self, opinion: str, user_id: int = None, username: str = None) -> Optional[UserOpinion]:
        if user_id is None and username is None:
            return None

        user_opinion = None

        if user_id is not None:
            user_opinion = self.get_user_opinion(user_id)

        if user_opinion is None and username is not None:
            all_users = self.get_all_user_opinions()
            for user in all_users:
                if user.username == username:
                    user_opinion = user
                    break

        if user_opinion is None:
            return None

        user_opinion.opinions.append(opinion)

        if len(user_opinion.opinions) > self.max_opinions:
            user_opinion.opinions.pop(0)

        self.database.update(
            self.table_name,
            {"opinions": user_opinion.opinions},
            {"user_id": user_opinion.user_id}
        )

        return user_opinion

    async def process_historical_messages(self):
        """
        Process historical messages for all users:
        1. Get all user_ids from user opinions
        2. For each user_id, fetch messages from the last 2 days from all chats
        3. Randomly select 10 messages
        4. Generate opinions based on these messages
        """
        if not self.chat_history:
            logging.warning("Chat history not available, skipping historical message processing")
            return

        logging.info("Starting to process historical messages for all users")

        # Get all user opinions
        all_users = self.get_all_user_opinions()

        # Get all chat_ids by listing directories in chat_logs_dir
        chat_logs_dir = self.chat_history.chat_logs_dir
        if not os.path.exists(chat_logs_dir):
            logging.warning(f"Chat logs directory {chat_logs_dir} does not exist")
            return

        chat_ids = []
        for item in os.listdir(chat_logs_dir):
            if os.path.isdir(os.path.join(chat_logs_dir, item)):
                try:
                    chat_id = int(item)
                    chat_ids.append(chat_id)
                except ValueError:
                    # Skip directories that are not valid chat_ids
                    pass

        if not chat_ids:
            logging.warning("No chat IDs found in chat logs directory")
            return

        logging.info(f"Found {len(chat_ids)} chat IDs: {chat_ids}")

        for user in all_users:
            user_id = user.user_id
            logging.info(f"Processing historical messages for user {user_id}")

            # Collect messages from all chats
            user_messages = []

            for chat_id in chat_ids:
                # Get messages for this chat for the last 2 days
                try:
                    messages_dict = self.chat_history.get_messages(chat_id=chat_id, days_limit=2)

                    # Filter messages by user_id
                    for date_str, chat_logs in messages_dict.items():
                        for chat_log in chat_logs:
                            if str(chat_log.user_id) == str(user_id):
                                user_messages.append(chat_log)
                except Exception as e:
                    logging.error(f"Error getting messages for chat {chat_id}: {e}")

            # If we have messages for this user
            if user_messages:
                logging.info(f"Found {len(user_messages)} messages for user {user_id} across all chats")

                # Randomly select up to 10 messages
                if len(user_messages) > 10:
                    selected_messages = random.sample(user_messages, 10)
                else:
                    selected_messages = user_messages

                # Make sure we have messages to process
                if selected_messages:
                    # Concatenate all selected messages into a single text
                    concatenated_messages = ""
                    # Use the first message to create the Message object
                    first_chat_log = selected_messages[0]
                    try:
                        # Create a Message object from the first ChatLog
                        from_obj = From(
                            id=int(first_chat_log.user_id),
                            first_name=first_chat_log.first_name,
                            last_name=first_chat_log.last_name,
                            username=first_chat_log.username
                        )

                        message = Message(
                            from_=from_obj,
                            text=""  # Will be set after concatenation
                        )

                        # Concatenate all messages
                        for chat_log in selected_messages:
                            concatenated_messages += chat_log.message + "\n"

                        # Set the concatenated text to the message
                        message.text = concatenated_messages.strip()

                        # Generate a single opinion based on all messages
                        await self.add_opinion_by_message_tone(concatenated_messages, message)
                    except Exception as e:
                        logging.error(f"Error processing messages for user {user_id}: {e}")
            else:
                self.add_opinion(user_id=user_id, opinion=random.choice(["Sumido.", "Desaparecido.", "Ausente.", "Não presente.", "Inexistente."]))

        logging.info("Finished processing historical messages for all users")

    async def adjust_mood(self, message: Message) -> (int, str):
        text = ""
        message_tone = 3
        user_id = message.from_.id

        if message.text:
            text = message.text
        elif message.caption:
            text = message.caption

        if text:
            message_tone = await self._check_message_tone(text, message=message)

        reaction = ""

        if message_tone == 5:
            self.adjust_mood_by_user_id(user_id=user_id, mood_adjustment=10.0)
            reaction = "🖕"
        if message_tone == 4:
            self.adjust_mood_by_user_id(user_id=user_id, mood_adjustment=2.5)
            reaction = random.choice(["🤬", "😡"])

        if message_tone == 2:
            self.adjust_mood_by_user_id(user_id=user_id, mood_adjustment=-1.0)
            reaction = random.choice(["🆒", "🗿"])
        if message_tone == 1:
            self.adjust_mood_by_user_id(user_id=user_id, mood_adjustment=-1.5)
            reaction = random.choice(["❤", "💘", "😘"])

        if message_tone == 0:
            reaction = random.choice(["🤔", "🥴", "🤨", "🙏", "🤷"])

            self.adjust_mood_by_user_id(user_id=user_id, mood_adjustment=-50.0)

        return message_tone, reaction
