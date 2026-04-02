from discord.abc import PrivateChannel
from discord.ext import tasks
import discord
import markovify
import logging
import os


handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')

# Token for the bot, not to be confused with the account token
TOKEN = os.environ.get("MARKOVBOT_TOKEN", "")
BOT_CHANNEL = int(os.environ.get("MARKOVBOT_CHANNEL_ID", 0))


def load_markov_model() -> markovify.NewlineText:
    logging.info("Loading messages.txt...")
    with open("messages.txt", encoding="utf-8") as f:
        text: str = f.read()

    logging.info("Creating NewlineText. This may take a while")
    return markovify.NewlineText(text)


logging.info("Registering intents...")
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
logging.info("Setting up client...")
client = discord.Client(intents=intents)
logging.info("Loading up markov model...")
text_model: markovify.NewlineText = load_markov_model()


@tasks.loop(minutes=60)
async def scout_thinks() -> None:
    channel: discord.VoiceChannel | discord.StageChannel | discord.ForumChannel | discord.TextChannel | discord.CategoryChannel | discord.Thread | PrivateChannel | None = client.get_channel(
        BOT_CHANNEL)
    if channel and isinstance(channel, discord.abc.Messageable):
        generated_response = text_model.make_sentence(
        ) or "OOC: I was unable to generate a message. Try again!"
        message = f"BS thinks: *{generated_response}*."
        await channel.send(message)


@client.event
async def on_ready() -> None:
    logging.info(f"Logged in as {client.user}")
    if not scout_thinks.is_running():
        scout_thinks.start()


@client.event
async def on_message(message: discord.Message) -> None:
    logging.info("Message received!")
    if message.author == client.user:
        return

    if not message.content.startswith("!talk"):
        return

    generated_response = ""
    stripped_message: str = message.content.replace("!talk", "").lstrip()

    if stripped_message != "":
        if len(stripped_message.split(" ")) > 2:
            await message.channel.send("OOC: You cannot have more than 2 words after the !talk command. Try again!")
        try:
            generated_response: str = text_model.make_sentence_with_start(
                stripped_message.replace("!talk", "").rstrip()) or "OOC: I was unable to generate a message. Try another term?"
        except Exception as e:
            generated_response = f"OOC: It may not have been possible to find a chain starting with {stripped_message}.\nError: {e}"
    else:
        generated_response = text_model.make_sentence(
        ) or "OOC: I was unable to generate a message. Try again!"

    logging.info("Sending generated response!")
    await message.channel.send(generated_response)

logging.info("Running client!")
client.run(TOKEN, log_handler=handler, root_logger=True)
