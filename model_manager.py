import os

import markovify
from loguru import logger

import botconfig


def save_model(state_size: int) -> None:
    with open("data/messages.txt", encoding="utf-8") as f:
        text: str = f.read()

        text_model = markovify.NewlineText(
            text, well_formed=False, state_size=state_size)
        text_model.compile(inplace=True)
        model_json: str = text_model.to_json()
        try:
            with open("data/markov_model.json", "w", encoding="utf-8") as model_file:
                model_file.write(model_json)
        except PermissionError as e:
            logger.error(
                f"Permission error while trying to save the model: {repr(e)}")
            logger.info(
                f"Permission is {os.access('data/markov_model.json', os.W_OK)}")


def load_model() -> markovify.NewlineText:
    try:
        with open("data/markov_model.json", "r", encoding="utf-8") as model_file:
            model_json: str = model_file.read()
            return markovify.NewlineText.from_json(model_json)
    except FileNotFoundError:
        logger.error(
            "markov_model.json not found. Please build the model first.")
        raise
    except PermissionError as e:
        logger.error(
            f"Permission error while trying to load the model: {repr(e)}")
        logger.info(
            f"Permission is {os.access('data/markov_model.json', os.R_OK)}")
        raise


def build_markov_model() -> markovify.NewlineText:
    logger.info("Loading messages.txt...")
    try:
        with open("data/messages.txt", "r", encoding="utf-8") as f:
            text: str = f.read()
    except FileNotFoundError:
        logger.error(
            "messages.txt not found. Please run the dataset generation script first.")
        raise
    except PermissionError as e:
        logger.error(
            f"Permission error while trying to load messages.txt: {repr(e)}")
        logger.info(
            f"Permission is {os.access('data/messages.txt', os.R_OK)}")
        raise

    logger.info("Creating NewlineText. This may take a while")
    return markovify.NewlineText(text, well_formed=False, state_size=botconfig.STATE_SIZE)
