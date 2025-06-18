# Internal
import logging

import asyncio
import random
import json
from asyncio import Semaphore

# External
import aiohttp


class LLM:
    def __init__(
            self,
            api_key: str,
            default_model: str = "gpt-4.1-nano",
    ):
        self.semaphore = Semaphore(2)
        self.api_key = api_key
        self.default_model = default_model

        self.session = aiohttp.ClientSession()

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def generate_text(
            self,
            prompt: str,
            model: str = "gpt-4.1-nano",
            temperature: float = 1.0,
    ) -> str:
        for i in range(3):
            retry_sleep = int(2 + random.random() * 5)
            try:
                async with self.semaphore:
                    model = model or self.default_model
                    is_chat_model = model != "gpt-3.5-turbo-instruct"

                    if is_chat_model:
                        # Chat models use the chat/completions endpoint
                        endpoint = "https://api.openai.com/v1/chat/completions"
                        request_data = {
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": temperature,
                        }
                    else:
                        # Completion models use the completions endpoint
                        endpoint = "https://api.openai.com/v1/completions"
                        request_data = {
                            "model": model,
                            "prompt": prompt,
                            "temperature": temperature,
                        }

                    async with self.session.post(
                            endpoint,
                            headers=self.headers,
                            json=request_data
                    ) as openai_request:
                        response = await openai_request.text()
                        response_json = json.loads(response)

                        if is_chat_model:
                            response_text = response_json['choices'][0]['message']['content']
                        else:
                            response_text = response_json['choices'][0]['text']

                        return response_text
            except Exception as exc:
                logging.exception(exc)
                await asyncio.sleep(retry_sleep)

        return "ué"
