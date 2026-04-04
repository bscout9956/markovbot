# Token for the bot, not to be confused with the account token
import os

TOKEN = os.environ.get("MARKOVBOT_TOKEN", "")
BOT_CHANNEL = int(os.environ.get("MARKOVBOT_CHANNEL_ID", 0))
TRY_COUNT = 50
STATE_SIZE = 3
