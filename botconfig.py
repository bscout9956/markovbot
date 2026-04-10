# Token for the bot, not to be confused with the account token
import os

TOKEN = os.environ.get("MARKOVBOT_TOKEN", "")
BOT_CHANNEL = int(os.environ.get("MARKOVBOT_CHANNEL_ID", 0))
TRY_COUNT = 50
STATE_SIZE = 3


# Enabling this will expose your hostname
# Do not enable if you don't know what you're doing
SHOW_HOSTNAME = bool(
    os.environ.get(
        "MARKOVBOT_SHOW_HOSTNAME",
        "False"
    ).lower() in ("true", "1", "t")
)
