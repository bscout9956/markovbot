import logging
import discord
import botconfig as botconfig


def load_discord_client() -> discord.Client:
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True
    return discord.Client(intents=intents)


def is_valid_channel(message: discord.Message) -> bool:
    is_correct_channel: bool = message.channel.id == botconfig.BOT_CHANNEL
    is_correct_forum: bool = getattr(
        message.channel, "parent_id", None) == botconfig.BOT_CHANNEL

    if not is_correct_channel and not is_correct_forum:
        logging.error(
            f"Message received in a channel that is not the bot channel. Message channel ID: {message.channel.id}, Bot channel ID: {botconfig.BOT_CHANNEL}")
        return False

    return True
