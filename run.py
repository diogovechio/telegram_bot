import asyncio

from pedro.main import TelegramBot

if __name__ == '__main__':
    decaptor = TelegramBot(
        bot_config_file='bot_configs.json',
        secrets_file='secrets.json',
        debug_mode=True,
    )

    asyncio.run(
        decaptor.run()
    )
