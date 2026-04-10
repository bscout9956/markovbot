
import asyncio
import gc
import os
import time

import discord
import markovify
from loguru import logger

import botconfig
import model_manager
import utils

# You may not want to log it to a file, fyi
# handler = logging.FileHandler(
#    filename='logs/discord.log', encoding='utf-8', mode='w')


def try_load_model() -> markovify.NewlineText:
    if not os.path.exists("data/markov_model.json"):
        logger.info(
            "markov_model.json not found. Loading messages.txt and creating model...")
        text_model: markovify.NewlineText = model_manager.build_markov_model()
        logger.info("Saving model to markov_model.json...")
        # model_manager.save_model(botconfig.STATE_SIZE)
        return text_model
    else:
        logger.info("markov_model.json found. Loading model...")
        return model_manager.load_model()


text_model: markovify.NewlineText = try_load_model()
text_model.compile(inplace=True)  # Compile the model for faster generation


def random_with_lookup(look_up_term: str) -> str:
    final_message = ""
    logger.info(f"Generating random message with lookup term: {look_up_term}")
    tries = 0
    max_tries = botconfig.TRY_COUNT * 10
    start: float = time.time()

    while tries < max_tries and final_message == "":
        generated_message: str = text_model.make_sentence(tries=10) or ""
        if look_up_term.lower() in generated_message.lower():
            final_message = generated_message
            end: float = time.time()
            time_taken: float = end - start
            final_message += f"\n\n*Note: It took {tries} tries and {time_taken:.4f} seconds to generate this message with the term '{look_up_term}'*"

        tries += 1

    return final_message


# Client code

client: discord.Client = utils.load_discord_client()


async def status_check() -> None:
    bot_channel = client.get_channel(botconfig.BOT_CHANNEL)
    if bot_channel and isinstance(bot_channel, discord.TextChannel):
        bot_message: str = f"## The bot is now **online**!\n ### Settings are 'TRY_COUNT': {botconfig.TRY_COUNT}, 'STATE_SIZE': {botconfig.STATE_SIZE}."
        if botconfig.SHOW_HOSTNAME:
            logger.warning(
                "SHOW_HOSTNAME is enabled. This will expose your hostname in the bot's status message.")
            logger.warning(
                "If you did not enable this intentionally, well...")
            import socket
            bot_message += f"\n ### Hostname: {socket.gethostname()}"
        await bot_channel.send(bot_message)

        gc.collect()


@client.event
async def on_ready() -> None:
    logger.info(f"Logged in as {client.user}")
    await status_check()


@client.event
async def on_message(message: discord.Message) -> None:
    logger.info(f"Message received from {message.author}.")

    if message.content == "" or message.author == client.user or not message.content.startswith("!"):
        return

    if not utils.is_valid_channel(message):
        return

    split_message: list[str] = message.content.rstrip().split(" ")
    cmd: str = split_message[0] or ""
    terms: list[str] = split_message[1:] if len(split_message) > 1 else []
    terms_str: str = " ".join(terms)

    if cmd not in ["!talk", "!randomtalk"]:
        logger.info(
            f"Message does not start with a recognized command. Message content: {message.content}")
        await message.channel.send(f"OOC: Unrecognized command {cmd}. Please use !talk or !randomtalk followed by a term to generate a message.")
        return  # Not sure why I need this return

    isTalk: bool = cmd == "!talk"
    isRandomTalk: bool = cmd == "!randomtalk"
    generated_response = ""

    try:
        if len(terms) > botconfig.STATE_SIZE - 1:
            await message.channel.send(f"OOC: You cannot have more than {botconfig.STATE_SIZE - 1} words after the {cmd} command. Try again!")
            gc.collect()

        if isTalk:
            generated_response: str = text_model.make_sentence_with_start(
                terms_str, tries=50
            ) or f"OOC: I tried {botconfig.TRY_COUNT} times and couldn't generate a message with {terms_str}. Try another term?"
        elif isRandomTalk:
            generated_response: str = await asyncio.to_thread(random_with_lookup, terms_str) or f"OOC: I tried to generate a random message with {terms_str} but failed. Try another term?"
        else:
            generated_response = "OOC: Unrecognized command. Please use !talk or !randomtalk followed by a term to generate a message."
    except Exception as e:
        logger.error(f"Error generating message: {e}")
        generated_response = f"OOC: An error occurred while generating the message. Details: {repr(e)}."

    if generated_response == "":
        generated_response = f"OOC: I couldn't generate a message with the term '{terms_str}'. Try another term?"

    await message.channel.send(generated_response)
    gc.collect()


client.run(botconfig.TOKEN)
