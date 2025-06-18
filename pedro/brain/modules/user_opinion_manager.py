# Internal
import random
import re
from dataclasses import asdict
from typing import List, Optional

# Project
from pedro.brain.modules.llm import LLM
from pedro.data_structures.user_opinion import UserOpinion
from pedro.data_structures.telegram_message import Message, From
from pedro.brain.modules.database import Database
from pedro.utils.text_utils import create_username


class UserOpinions:
    def __init__(self, database: Database, llm: LLM, max_opinions: int = 10):
        self.database = database
        self.llm = llm
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

        return self.moods_levels[level]

    def get_user_opinion(self, user_id: int) -> Optional[UserOpinion]:
        results = self.database.search(self.table_name, {"user_id": user_id})
        if results:
            return UserOpinion(**results[0])
        return None

    def get_all_user_opinions(self) -> List[UserOpinion]:
        results = self.database.get_all(self.table_name)
        return [UserOpinion(**data) for data in results]

    def adjust_mood_by_user_id(self, user_id: int, mood_adjustment: float) -> Optional[UserOpinion]:
        user_opinion = self.get_user_opinion(user_id)
        if not user_opinion:
            return None

        # Adjust the mood
        user_opinion.my_mood_with_him += mood_adjustment

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
                await self._add_opinion_by_message_tone(text, message=message)
            elif random.random() < 0.5:
                await self._add_opinion_by_message_tone(text, message=message)

            return int(return_num)

        return 3

    async def _add_opinion_by_message_tone(self, text: str, message: Message) -> Optional[UserOpinion]:
        prompt = (f"Dada a mensagem {text} enviada por "
                  f"{create_username(first_name=message.from_.first_name, username=message.from_.username)}, "
                  f"resuma em uma frase a sua opinião sobre ele."
                  f"Caso seja incapaz de gerar alguma opinião com base na mensagem fornecida, retorne 'None'")

        opinion = await self.llm.generate_text(prompt)

        if "none" not in opinion.lower():
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

    async def adjust_mood(self, message: Message) -> (int, str):
        text = ""
        user_id = message.from_.id
        if message.text:
            text = message.text

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

            self.adjust_mood_by_user_id(user_id=user_id, mood_adjustment=-10.0)

        return message_tone, reaction
