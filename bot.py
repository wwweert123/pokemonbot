import logging
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

import pokebase as pb

import os
from dotenv import load_dotenv

from db import SessionLocal
from alembic.model import CaughtPokemon

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


LOWER_MESSAGE_THRESHOLD = 10  # Minimum messages to trigger a spawn
UPPER_MESSAGE_THRESHOLD = 20  # Maximum messages to trigger a spawn
RESPAWN_THRESHOLD = 30  # Number of messages to trigger a respawn


spawn_counters = {}  # chat_id -> int
spawn_thresholds = {}  # chat_id -> int
spawn_state = {}
activation_state = {}


async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    activation_state[chat_id] = True
    await context.bot.send_message(
        chat_id=chat_id,
        text="Pokémon will begin spawning.",
    )


async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    activation_state[chat_id] = False
    await context.bot.send_message(
        chat_id=chat_id,
        text="Pokémon will stop spawning.",
    )


async def spawn_wild_pokemon(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    pokemon = pb.pokemon(random.randint(1, 1025))  # 1025 Pokémon

    if pokemon.sprites.front_default:
        # Send image of the Pokémon
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=pokemon.sprites.front_default,
            caption=(
                "👀 A wild Pokémon has appeared!\n" "Use /catch <name> to catch it!"
            ),
        )

        spawn_state[chat_id] = {"name": pokemon.species.name, "caught": False}
        print(pokemon.name)

    return True


# Reset spawn counters
def reset_counter(chat_id):
    spawn_counters[chat_id] = 0
    spawn_thresholds[chat_id] = random.randint(
        LOWER_MESSAGE_THRESHOLD, UPPER_MESSAGE_THRESHOLD
    )


# Set initial threshold for group
def init_group(chat_id):
    if chat_id not in spawn_thresholds:
        activation_state[chat_id] = False
        reset_counter(chat_id)


# Main message listener (non-command messages)
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get Chat object
    chat = update.effective_chat

    # Ignore non-group chats
    if chat.type not in ["group", "supergroup"]:
        return

    chat_id = chat.id

    # Initialize state and counters for the group if not already done
    init_group(chat_id)

    # Ignore groups on stop
    if not activation_state[chat_id]:
        return

    # Increment the spawn counter for the group
    spawn_counters[chat_id] += 1

    if (
        spawn_state.get(chat_id) is None
        and spawn_counters[chat_id] >= spawn_thresholds[chat_id]
    ):
        reset_counter(chat_id)
        await spawn_wild_pokemon(chat_id, context)
    elif spawn_counters[chat_id] >= RESPAWN_THRESHOLD:
        reset_counter(chat_id)
        await spawn_wild_pokemon(chat_id, context)


def update_user_pokemon_db(user_id: int, pokemon_name: str):
    try:
        with SessionLocal() as session:
            new_caught_pokemon = CaughtPokemon(
                user_id=user_id, pokemon_name=pokemon_name
            )
            session.add(new_caught_pokemon)
            session.commit()
    except Exception:
        logging.error(
            f"Error updating user {user_id} with caught Pokémon {pokemon_name}"
        )


async def catch_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in spawn_state:
        await context.bot.send_message(
            chat_id=chat_id,
            text="No Pokémon has appeared yet! Keep chatting to spawn one.",
        )
        return

    if len(context.args) == 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Please specify the Pokémon name to catch.",
        )
        return

    pokemon_name = " ".join(context.args).lower()
    if pokemon_name == spawn_state[chat_id].get("name", "").lower():

        # Update user profile with caught Pokémon
        user_id = update.effective_user.id
        update_user_pokemon_db(user_id, spawn_state[chat_id]["name"])

        # Remove the spawn state for this group
        spawn_state.pop(chat_id, None)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Congratulations! You caught {pokemon_name.capitalize()}!",
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"{pokemon_name.capitalize()} is not the Pokémon that appeared"
                "! Try again."
            ),
        )


def get_user_pokemons_db(user_id: int):
    try:
        with SessionLocal() as session:
            pokemons = (
                session.query(CaughtPokemon)
                .filter(CaughtPokemon.user_id == user_id)
                .all()
            )
            return {
                pokemon.pokemon_name: pokemons.count(pokemon) for pokemon in pokemons
            }
    except Exception:
        logging.error(f"Error retrieving Pokémon for user {user_id}")
        return {}


async def view_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    user_caught_pokemons = get_user_pokemons_db(user_id)
    if not user_caught_pokemons:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You have not caught any Pokémon yet!",
        )
        return

    # Format the response
    text = ""
    for pokemon, count in user_caught_pokemons.items():
        text += f"{pokemon.capitalize()} - {count}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


if __name__ == "__main__":
    load_dotenv()  # Load environment variables from .env file
    bot_token = os.getenv("BOT_TOKEN")

    application = ApplicationBuilder().token(bot_token).build()

    start_handler = CommandHandler("start", start_bot)
    stop_handler = CommandHandler("stop", stop_bot)
    catch_pokemon_handler = CommandHandler("catch", catch_pokemon)
    view_pokemon_handler = CommandHandler("mypokemon", view_pokemon)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), on_message)

    application.add_handler(start_handler)
    application.add_handler(stop_handler)
    application.add_handler(catch_pokemon_handler)
    application.add_handler(view_pokemon_handler)
    application.add_handler(message_handler)

    application.run_polling()
