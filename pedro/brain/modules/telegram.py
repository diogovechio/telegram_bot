# Internal
import asyncio
import logging
import typing as T
import json
import sys
import random

# External
import aiohttp

# Project
from pedro.data_structures.telegram_message import Message, MessagesResults, MessageReceived
from pedro.data_structures.max_size_list import MaxSizeList


class Telegram:
    def __init__(
        self,
        token: str,
        semaphore: int = 3,
        polling_rate: int = 1
    ):
        self._api_route = f"https://api.telegram.org/bot{token}"
        self._semaphore = asyncio.Semaphore(semaphore)
        self._polling_rate = polling_rate

        self._last_id = 0
        self._messages = MessagesResults()
        self._interacted_updates = MaxSizeList(50)

        self._session = aiohttp.ClientSession()

        asyncio.create_task(self._message_polling())

    async def get_new_message(self) -> T.AsyncGenerator[MessageReceived, None]:
        if self._messages.result:
            for message in self._messages.result:
                message: MessageReceived

                if message.update_id not in self._interacted_updates:
                    yield message

                    self._interacted_updates.append(message.update_id)

    async def _message_polling(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._polling_rate)

                polling_url = f"{self._api_route}/getUpdates?offset={self._last_id}"

                async with self._session.get(polling_url) as request:
                    if 200 <= request.status < 300:
                        response = json.loads((await request.text()).replace('"from":{"', '"from_":{"'))
                        if 'ok' in response and response['ok']:
                            self._messages = MessagesResults(**response)
                            if self._messages.result:
                                self._last_id = self._messages.result[-1].update_id
            except Exception as exc:
                logging.exception(exc)
                await asyncio.sleep(15)

    async def image_downloader(
            self,
            message: Message,
    ) -> T.Optional[bytes]:
        async with self._session.get(
                f"{self._api_route}/getFile?file_id={message.photo[-1].file_id}") as request:
            if 200 <= request.status < 300:
                response = json.loads(await request.text())
                if 'ok' in response and response['ok']:
                    file_path = response['result']['file_path']
                    async with self._session.get(f"{self._api_route.replace('.org/bot', '.org/file/bot')}/"
                                                f"{file_path}") as download_request:
                        if 200 <= download_request.status < 300:
                            return await download_request.read()
                        else:
                            logging.critical(f"Image download failed: {download_request.status}")

    async def send_photo(self, image: bytes, chat_id: int, caption=None, reply_to=None, sleep_time=0, max_retries=5) -> None:
        await asyncio.sleep(sleep_time)

        for _ in range(max_retries):
            async with self._semaphore:
                async with self._session.post(
                        url=f"{self._api_route}/sendPhoto".replace('\n', ''),
                        data=aiohttp.FormData(
                            (
                                    ("chat_id", str(chat_id)),
                                    ("photo", image),
                                    ("reply_to_message_id", str(reply_to) if reply_to else ''),
                                    ('allow_sending_without_reply', 'true'),
                                    ("caption", caption if caption else '')
                            )
                        )
                ) as resp:
                    logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")
                    if 200 <= resp.status < 300:
                        break
            await asyncio.sleep(10)

    async def send_video(self, video: bytes, chat_id: int, reply_to=None, sleep_time=0) -> None:
        await asyncio.sleep(sleep_time)

        async with self._semaphore:
            async with self._session.post(
                    url=f"{self._api_route}/sendVideo".replace('\n', ''),
                    data=aiohttp.FormData(
                        (
                                ("chat_id", str(chat_id)),
                                ("video", video),
                                ("reply_to_message_id", str(reply_to) if reply_to else ''),
                                ('allow_sending_without_reply', 'true'),
                        )
                    )
            ) as resp:
                logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

    async def send_voice(self, audio: bytes, chat_id: int, reply_to=None, sleep_time=0) -> None:
        await asyncio.sleep(sleep_time)

        async with self._semaphore:
            async with self._session.post(
                    url=f"{self._api_route}/sendVoice".replace('\n', ''),
                    data=aiohttp.FormData(
                        (
                                ("chat_id", str(chat_id)),
                                ("voice", audio),
                                ("reply_to_message_id", str(reply_to) if reply_to else ''),
                                ('allow_sending_without_reply', 'true'),
                        )
                    )
            ) as resp:
                logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

    async def send_action(
            self,
            chat_id: int,
            action: T.Union[T.Literal['typing'], T.Literal['upload_photo'], T.Literal['find_location']] = 'typing',
            repeats=False
    ) -> None:
        while True:
            async with self._semaphore:
                async with self._session.post(
                        url=f"{self._api_route}/sendChatAction".replace('\n', ''),
                        data=aiohttp.FormData(
                            (
                                ("chat_id", str(chat_id)),
                                ('action', action),
                            )
                        )
                ) as resp:
                    logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

            if not repeats:
                break

            await asyncio.sleep(round(5 + (random.random() * 2)))

    async def send_document(self, document: bytes, chat_id: int, caption=None, reply_to=None, sleep_time=0) -> None:
        await asyncio.sleep(sleep_time)

        async with self._semaphore:
            async with self._session.post(
                    url=f"{self._api_route}/sendDocument".replace('\n', ''),
                    data=aiohttp.FormData(
                        (
                                ("chat_id", str(chat_id)),
                                ("document", document),
                                ("caption", caption if caption else ''),
                                ("reply_to_message_id", str(reply_to) if reply_to else ''),
                                ('allow_sending_without_reply', 'true'),
                        )
                    )
            ) as resp:
                logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

    async def forward_message(
            self,
            target_chat_id: int,
            from_chat_id: int,
            message_id: int,
            sleep_time=0,
            replace_token: T.Optional[str] = None
    ) -> int:
        await asyncio.sleep(sleep_time)
        url = self._api_route
        if replace_token:
            url = f"https://api.telegram.org/bot{replace_token}"

        async with self._semaphore:
            async with self._session.post(
                    url=f"{url}/forwardMessage".replace('\n', ''),
                    data=aiohttp.FormData(
                        (
                            ("chat_id", str(target_chat_id)),
                            ("from_chat_id", str(from_chat_id)),
                            ("message_id", str(message_id)),
                        )
                    )
            ) as resp:
                logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

                return resp.status

    async def send_message(
            self,
            message_text: str,
            chat_id: int,
            reply_to=None,
            sleep_time=0,
            parse_mode: str = "Markdown",
            disable_notification=False,
            max_retries=7
    ) -> None:
        fallback_parse_modes = ["", "HTML", "MarkdownV2", "Markdown"]

        await asyncio.sleep(sleep_time)

        for i in range(max_retries):
            async with self._semaphore:
                async with self._session.post(
                        f"{self._api_route}/sendMessage".replace('\n', ''),
                        json={
                            "chat_id": chat_id,
                            'reply_to_message_id': reply_to,
                            'allow_sending_without_reply': True,
                            'text': message_text,
                            'disable_notification': disable_notification,
                            'parse_mode': parse_mode
                        }
                ) as resp:
                    logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

                    if 200 <= resp.status < 300:
                        break
                    parse_mode = fallback_parse_modes.pop() if len(fallback_parse_modes) else ""

    async def leave_chat(self, chat_id: int, sleep_time=0) -> None:
        await asyncio.sleep(sleep_time)

        async with self._session.post(
                f"{self._api_route}/leaveChat".replace('\n', ''),
                json={"chat_id": chat_id}
        ) as resp:
            logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        async with self._session.post(
                f"{self._api_route}/deleteMessage".replace('\n', ''),
                json={
                    "chat_id": chat_id,
                    "message_id": message_id
                }
        ) as resp:
            logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")

    async def set_chat_title(self, chat_id: int, title: str) -> None:
        async with self._session.post(
                f"{self._api_route}/setChatTitle".replace('\n', ''),
                json={
                    "chat_id": chat_id,
                    "title": title
                }
        ) as resp:
            logging.info(f"{sys._getframe().f_code.co_name} - {resp.status}")
