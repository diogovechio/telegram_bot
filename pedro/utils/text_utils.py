# Internal
import math
import random
import re

# Project



def create_username(first_name: str, username: str | None) -> str:
    if username:
        return f"@{username}"

    return first_name.lower()


def remove_hashtags(text: str) -> str:
    new_text = re.sub(r'#\w+', '', text)
    return new_text


def remove_emojis(text: str) -> str:
    text = text.replace(
        "!", "...").replace(
        ";)", "").replace(
        ":)", "").replace(
        ":(", "").replace(
        ":p", "").replace(
        ";p", "")

    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # símbolos e sinais
                               u"\U0001F680-\U0001F6FF"  # transporte e mapa de símbolos
                               u"\U0001F1E0-\U0001F1FF"  # bandeiras (IOS)
                               u"\U00002702-\U000027B0"  # outros sinais
                               u"\U000024C2-\U0001F251" 
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


def list_crop(l: list, max_size: int) -> list:
    if not len(l):
        return l

    def round_up(n, decimals=0):
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier

    jump = int(round_up(len(l) / max_size))

    new_list = []
    for i in range(jump - 1, len(l), jump):
        new_list.append(l[i])
    return new_list


async def adjust_pedro_casing(
        original_message: str,
        clean_prompts: dict | None = None
) -> str:
    try:
        ai_message = ""
        idx_to_lower = 0
        if "```" not in original_message and len(original_message) > 1:
            original_message = original_message.strip()
            for i, letter in enumerate(original_message):
                next_idx = i + 1
                if idx_to_lower == i:
                    if (len(original_message) - 1 != next_idx) and not original_message[next_idx].isupper():
                        letter = letter.lower()
                ai_message += letter

                if letter in (".", "!", "?", ":"):
                    idx_to_lower = i + 2
                elif letter in ('"', "\n"):
                    idx_to_lower = i + 1

            if ai_message.count(".") == 1 and ai_message[-1] == ".":
                ai_message = ai_message.replace(".", "")

            if clean_prompts:
                for _, msg in clean_prompts.items():
                    ai_message = ai_message.replace(msg, '')

            if ai_message.lower().strip().startswith("pedro:"):
                ai_message = ai_message.replace("pedro: ", "rs, ")

            if ai_message:
                while any(word in ai_message[0] for word in ['.', ',', '?', '\n', ' ', '!']):
                    ai_message = ai_message[1:]

                if '"' in ai_message[0] and '"' in ai_message[-1]:
                    ai_message = ai_message.replace('"', "")

                if random.random() < 0.02 or "desculp" in ai_message.split(" ")[0].lower():
                    ai_message = ai_message.upper()

                if ai_message.startswith("ah,"):
                    ai_message = ai_message.replace("ah, ", "")

                if len(ai_message) > 1 and ai_message[1].islower():
                    new_message = ""
                    for i, letter in enumerate(ai_message):
                        if i == 0:
                            letter = letter.lower()

                        new_message += letter

                    ai_message = new_message

                return re.sub(' +', ' ', ai_message)
            elif len(original_message):
                return original_message.upper()
            else:
                return 'estou sem palavras' if round(random.random()) else 'tenho nada a dizer'
    except Exception as exc:
        # get_running_loop().create_task(telegram_logging(exc))

        if len(original_message):
            return original_message.upper()

        return '@diogovechio dei pau vai ver o log'

    return original_message
