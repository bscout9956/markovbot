from datetime import datetime, timedelta

from discord.abc import PrivateChannel
from discord.ext import tasks
import discord
import markovify
import logging
import os
import asyncio

# You may not want to log it to a file, fyi
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')

# Token for the bot, not to be confused with the account token
TOKEN = os.environ.get("MARKOVBOT_TOKEN", "")
BOT_CHANNEL = int(os.environ.get("MARKOVBOT_CHANNEL_ID", 0))
TRY_COUNT = 50
STATE_SIZE = 3


def load_markov_model() -> markovify.NewlineText:
    logging.info("Loading messages.txt...")
    with open("messages.txt", encoding="utf-8") as f:
        text: str = f.read()

    logging.info("Creating NewlineText. This may take a while")
    return markovify.NewlineText(text, well_formed=False, state_size=STATE_SIZE)


intents: discord.Intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
text_model: markovify.NewlineText = load_markov_model()
text_model.compile()


@tasks.loop(minutes=60)
async def scout_thinks() -> None:
    channel: discord.VoiceChannel | discord.StageChannel | discord.ForumChannel | discord.TextChannel | discord.CategoryChannel | discord.Thread | PrivateChannel | None = client.get_channel(
        BOT_CHANNEL)
    if channel and isinstance(channel, discord.abc.Messageable):
        generated_response = text_model.make_sentence(
            tries=TRY_COUNT) or f"OOC: I tried {TRY_COUNT} but I was unable to generate a message for some reason..."
        message = f"BS thinks: *{generated_response}*.\n*Next message will be sent at: {datetime.now() + timedelta(hours=1)} UTC-3*"
        await channel.send(message)


@client.event
async def on_ready() -> None:
    logging.info(f"Logged in as {client.user}")
    if not scout_thinks.is_running():
        scout_thinks.start()


def random_with_lookup(look_up_term) -> str:
    final_message = ""
    logging.info(f"Generating random message with lookup term: {look_up_term}")
    tries = 0
    while tries < TRY_COUNT * 10 and final_message == "":
        generated_message = text_model.make_sentence(tries=10) or ""
        if look_up_term in generated_message:
            final_message = generated_message
        tries += 1

    logging.info(
        f"Final message generated with lookup term {look_up_term}: {final_message}")
    return final_message


@client.event
async def on_message(message: discord.Message) -> None:
    logging.info(f"Message received from {message.author}.")

    if message.content == "":
        return

    if not message.content.startswith("!"):
        return

    if message.author == client.user:
        return

    is_correct_channel: bool = message.channel.id == BOT_CHANNEL
    is_correct_forum: bool = getattr(
        message.channel, "parent_id", None) == BOT_CHANNEL
    if not is_correct_channel and not is_correct_forum:
        logging.error(
            f"Message received in a channel that is not the bot channel. Message channel ID: {message.channel.id}, Bot channel ID: {BOT_CHANNEL}")
        return

    isTalk = message.content.startswith("!talk")
    isRandomTalk = message.content.startswith("!randomtalk")
    generated_response = ""

    if isTalk or isRandomTalk:
        cmd = "!randomtalk" if isRandomTalk else "!talk"
        stripped_message = message.content.replace(cmd, "").lstrip()

        if isTalk:
            if len(stripped_message.split(" ")) > STATE_SIZE:
                await message.channel.send("OOC: You cannot have more than 2 words after the !talk command. Try again!")

            try:
                generated_response: str = text_model.make_sentence_with_start(stripped_message.replace(
                    "!talk", "").rstrip(), tries=50) or f"OOC: I tried {TRY_COUNT} times and couldn't generate a message with {stripped_message}. Try another term?"
            except Exception as e:
                generated_response = f"OOC: It may not have been possible to find a chain starting with {stripped_message}.\nError: {repr(e)}"
        if isRandomTalk:
            if len(stripped_message.split(" ")) > STATE_SIZE - 1:
                await message.channel.send("OOC: You cannot have more than 1 word after the !randomtalk command. Try again!")

            try:
                generated_response: str = await asyncio.to_thread(random_with_lookup, stripped_message) or f"OOC: I tried {TRY_COUNT} times and couldn't generate a random message with {stripped_message}. Try another term?"
            except Exception as e:
                generated_response = f"OOC: It may not have been possible to find a message containing {stripped_message} as part of the generated random message.\nError: {repr(e)}"

    if generated_response != "" and (isTalk or isRandomTalk):
        await message.channel.send(generated_response)

client.run(TOKEN, log_handler=handler, root_logger=True)
