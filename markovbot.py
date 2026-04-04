from datetime import datetime, timedelta

from discord.abc import PrivateChannel
from discord.ext import tasks
import discord
import markovify
import logging
import os
import asyncio
import time

import botconfig
import model_manager

# You may not want to log it to a file, fyi
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')


def load_markov_model() -> markovify.NewlineText:
    logging.info("Loading messages.txt...")
    with open("messages.txt", encoding="utf-8") as f:
        text: str = f.read()

    logging.info("Creating NewlineText. This may take a while")
    return markovify.NewlineText(text, well_formed=False, state_size=botconfig.STATE_SIZE)


def load_discord_client() -> discord.Client:
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True
    return discord.Client(intents=intents)


def try_load_model() -> markovify.NewlineText:
    if not os.path.exists("markov_model.json"):
        logging.info(
            "markov_model.json not found. Loading messages.txt and creating model...")
        text_model: markovify.NewlineText = load_markov_model()
        logging.info("Saving model to markov_model.json...")
        model_manager.save_model(botconfig.STATE_SIZE)
        return text_model
    else:
        logging.info("markov_model.json found. Loading model...")
        return model_manager.load_model()


text_model: markovify.NewlineText = try_load_model()


def random_with_lookup(look_up_term: str) -> str:
    final_message = ""
    logging.info(f"Generating random message with lookup term: {look_up_term}")
    tries = 0
    max_tries = botconfig.TRY_COUNT * 10
    start = time.time()

    if look_up_term not in text_model.chain.model:
        return f"OOC: The term '{look_up_term}' was not found in the model. Try another term?"

    while tries < max_tries and final_message == "":
        generated_message = text_model.make_sentence(tries=10) or ""
        if look_up_term.lower() in generated_message.lower():
            final_message = generated_message
            end = time.time()
            time_taken = end - start
            final_message += f"\n\n*Note: It took {tries} tries and {time_taken:.4f} seconds to generate this message with the term '{look_up_term}'*"

        tries += 1

    return final_message

# Tasks and stuff


@tasks.loop(minutes=60)
async def scout_thinks() -> None:
    channel: discord.VoiceChannel | discord.StageChannel | discord.ForumChannel | discord.TextChannel | discord.CategoryChannel | discord.Thread | PrivateChannel | None = client.get_channel(
        botconfig.BOT_CHANNEL)
    if channel and isinstance(channel, discord.abc.Messageable):
        generated_response = text_model.make_sentence(
            tries=botconfig.TRY_COUNT) or f"OOC: I tried {botconfig.TRY_COUNT} but I was unable to generate a message for some reason..."
        message = f"BS thinks: *{generated_response}*.\n*Next message will be sent at: {datetime.now() + timedelta(hours=1)} UTC-3*"
        await channel.send(message)

client: discord.Client = load_discord_client()

# Client code


@client.event
async def on_ready() -> None:
    logging.info(f"Logged in as {client.user}")
    if not scout_thinks.is_running():
        scout_thinks.start()


@client.event
async def on_message(message: discord.Message) -> None:
    logging.info(f"Message received from {message.author}.")

    if message.content == "" or message.author == client.user or not message.content.startswith("!"):
        return

    is_correct_channel: bool = message.channel.id == botconfig.BOT_CHANNEL
    is_correct_forum: bool = getattr(
        message.channel, "parent_id", None) == botconfig.BOT_CHANNEL

    if not is_correct_channel and not is_correct_forum:
        logging.error(
            f"Message received in a channel that is not the bot channel. Message channel ID: {message.channel.id}, Bot channel ID: {botconfig.BOT_CHANNEL}")
        return

    isTalk = message.content.startswith("!talk")
    isRandomTalk = message.content.startswith("!randomtalk")
    generated_response = ""

    if isTalk or isRandomTalk:
        cmd = "!randomtalk" if isRandomTalk else "!talk"
        stripped_message = message.content.replace(cmd, "").lstrip()

        if isTalk:
            if len(stripped_message.split(" ")) > botconfig.STATE_SIZE:
                await message.channel.send("OOC: You cannot have more than 2 words after the !talk command. Try again!")

            try:
                generated_response: str = text_model.make_sentence_with_start(stripped_message.replace(
                    "!talk", "").rstrip(), tries=50) or f"OOC: I tried {botconfig.TRY_COUNT} times and couldn't generate a message with {stripped_message}. Try another term?"
            except Exception as e:
                generated_response = f"OOC: It may not have been possible to find a chain starting with {stripped_message}.\nError: {repr(e)}"
        if isRandomTalk:
            if len(stripped_message.split(" ")) > botconfig.STATE_SIZE - 1:
                await message.channel.send("OOC: You cannot have more than 1 word after the !randomtalk command. Try again!")

            try:
                generated_response: str = await asyncio.to_thread(random_with_lookup, stripped_message) or f"OOC: I tried to generate a random message with {stripped_message} but failed. Try another term?"
            except Exception as e:
                generated_response = f"OOC: It may not have been possible to find a message containing {stripped_message} as part of the generated random message.\nError: {repr(e)}"

    if generated_response != "" and (isTalk or isRandomTalk):
        await message.channel.send(generated_response)

client.run(botconfig.TOKEN, log_handler=handler, root_logger=True)
