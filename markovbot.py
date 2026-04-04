
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


client: discord.Client = load_discord_client()

# Client code


async def status_check() -> None:
    bot_channel = client.get_channel(botconfig.BOT_CHANNEL)
    if bot_channel and isinstance(bot_channel, discord.TextChannel):
        await bot_channel.send("## The bot is now **online**!")


@client.event
async def on_ready() -> None:
    logging.info(f"Logged in as {client.user}")
    await status_check()


def is_valid_channel(message: discord.Message) -> bool:
    is_correct_channel: bool = message.channel.id == botconfig.BOT_CHANNEL
    is_correct_forum: bool = getattr(
        message.channel, "parent_id", None) == botconfig.BOT_CHANNEL

    if not is_correct_channel and not is_correct_forum:
        logging.error(
            f"Message received in a channel that is not the bot channel. Message channel ID: {message.channel.id}, Bot channel ID: {botconfig.BOT_CHANNEL}")
        return False

    return True


@client.event
async def on_message(message: discord.Message) -> None:
    logging.info(f"Message received from {message.author}.")

    if message.content == "" or message.author == client.user or not message.content.startswith("!"):
        return

    if not is_valid_channel(message):
        return

    split_message: list[str] = message.content.rstrip().split(" ")
    cmd: str = split_message[0] or ""
    terms: list[str] = split_message[1:] if len(split_message) > 1 else []
    terms_str: str = " ".join(terms)

    if cmd not in ["!talk", "!randomtalk"]:
        logging.info(
            f"Message does not start with a recognized command. Message content: {message.content}")
        await message.channel.send(f"OOC: Unrecognized command {cmd}. Please use !talk or !randomtalk followed by a term to generate a message.")
        return  # Not sure why I need this return

    isTalk: bool = cmd == "!talk"
    isRandomTalk: bool = cmd == "!randomtalk"
    generated_response = ""

    try:
        if isTalk:
            if len(terms) > botconfig.STATE_SIZE - 1:
                await message.channel.send(f"OOC: You cannot have more than {botconfig.STATE_SIZE - 1} words after the !talk command. Try again!")

            generated_response: str = text_model.make_sentence_with_start(
                terms_str, tries=50
            ) or f"OOC: I tried {botconfig.TRY_COUNT} times and couldn't generate a message with {terms_str}. Try another term?"
        elif isRandomTalk:
            if len(terms) > botconfig.STATE_SIZE - 1:
                await message.channel.send(f"OOC: You cannot have more than {botconfig.STATE_SIZE - 1} words after the !randomtalk command. Try again!")

                generated_response: str = await asyncio.to_thread(random_with_lookup, terms_str) or f"OOC: I tried to generate a random message with {terms_str} but failed. Try another term?"
        else:
            generated_response = "OOC: Unrecognized command. Please use !talk or !randomtalk followed by a term to generate a message."
    except Exception as e:
        logging.error(f"Error generating message: {e}")
        generated_response = f"OOC: An error occurred while generating the message. Details: {repr(e)}."

    await message.channel.send(generated_response)

client.run(botconfig.TOKEN, log_handler=handler, root_logger=True)
