from youtube_transcript_api import YouTubeTranscriptApi
from bs4 import BeautifulSoup
import logging
import aiohttp

from pedro.data_structures.telegram_message import Message


async def https_url_extract(text: str) -> str:
    final_text = ""
    text = text[text.find('https://'):]
    for letter in text:
        if letter == " " or letter == "\n":
            break
        final_text += letter
    if "https://" in final_text:
        return final_text
    else:
        return ""


async def youtube_caption_extractor(url: str, char_limit: int) -> str:
    try:
        if "watch?v=" in url and "youtube" in url:
            video_id = url.split("watch?v=")[-1]
        elif "youtu.be" in url or "shorts" in url:
            video_id = url.split("/")[-1]
        else:
            return ""

        a = YouTubeTranscriptApi.get_transcript(video_id, ['pt-BR', 'pt', 'pt-PT', 'en', 'en-US'])

        text = "\n".join([i['text'] for i in a if 'text' in i])
        if len(text) > char_limit:
            text = text[:int(char_limit / 2)] + text[-int(char_limit / 2):]

        return text
    except Exception as exc:
        logging.exception(exc)
        # get_running_loop().create_task(telegram_logging(exc))

        return ""


async def html_paragraph_extractor(text: str, char_limit: int) -> str:
    soup = BeautifulSoup(text, 'html.parser')
    if soup.find("article"):
        tag = soup.article

    elif soup.find("main"):
        tag = soup.main

    elif soup.find("body"):
        tag = soup.body

    else:
        return ""

    final_text = "\n".join(
        [text for text in tag.strings
         if len(text.strip()) > 1]
    )

    if len(final_text) < 500:
        if soup.find("main"):
            tag = soup.main

        elif soup.find("body"):
            tag = soup.body

        new_text = "\n".join(
            [text for text in tag.strings
             if len(text.strip()) > 1]
        )

        if len(new_text) > len(final_text):
            final_text = new_text

    if len(final_text) > char_limit:
        final_text = final_text[:int(char_limit / 2)] + final_text[-int(char_limit / 2):]

    return final_text


async def extract_website_paragraph_content(
        url: str,
        session: aiohttp.ClientSession,
        char_limit=11000
) -> str:
    try:
        if "youtube.com/" in url or "https://youtu.be" in url:
            text = await youtube_caption_extractor(url, char_limit)

        else:
            headers = {"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) "
                                     "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}
            async with session.get(url, headers=headers) as site:
                text = await html_paragraph_extractor(await site.text(), char_limit)

        if len(text) >= 10:
            return "... responda ou sumarize com base no texto a seguir:\n\n" + text

    except Exception as exc:
        # get_running_loop().create_task(telegram_logging(exc))
        logging.exception(exc)

    return f"essa URL parece inacessível: {url} - opine sobre o que acha que se trata a URL e finalize dizendo que " \
           f"é só sua opinião e que você não conseguiu acessar a URL"


async def check_and_update_with_url_contents(message: Message) -> Message:
    async def _process_text_with_url(text: str, session: aiohttp.ClientSession) -> str:
        if not text:
            return text

        if url_detector := await https_url_extract(text):
            url_content = await extract_website_paragraph_content(
                url=url_detector,
                session=session
            )
            return text.replace(url_detector, url_content)
        return text

    async with aiohttp.ClientSession() as session:
        if message.text:
            message.text = await _process_text_with_url(message.text, session)

        if message.reply_to_message and message.reply_to_message.text:
            message.reply_to_message.text = await _process_text_with_url(message.reply_to_message.text, session)

        if message.caption:
            message.caption = await _process_text_with_url(message.caption, session)

    return message
