import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

import pokebase as pb

import os
from dotenv import load_dotenv

from db import SessionLocal
from alembic.model import CaughtPokemon

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


LOWER_MESSAGE_THRESHOLD = 1  # Minimum messages to trigger a spawn
UPPER_MESSAGE_THRESHOLD = 5  # Maximum messages to trigger a spawn
RESPAWN_THRESHOLD = 15       # Number of messages to trigger a respawn


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a pokemon bot! Use /help to see available commands.")


spawn_counters = {}       # group_id -> int
spawn_thresholds = {}     # group_id -> int
spawn_state = {}


async def spawn_wild_pokemon(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    pokemon = pb.pokemon(random.randint(1, 1025))  # Assuming there are 1025 Pokémon

    if pokemon.sprites.front_default:
        # Send image of the Pokémon
        await context.bot.send_photo(chat_id=chat_id, photo=pokemon.sprites.front_default, caption="👀 A wild Pokémon has appeared! Use /catch <name> to catch it!")

        spawn_state[chat_id] = {
            "name": pokemon.name,
            "caught": False
        }
        print(pokemon.name)
    
    return True


# Reset spawn counters
def set_counters(group_id):
    spawn_counters[group_id] = 0
    spawn_thresholds[group_id] = random.randint(LOWER_MESSAGE_THRESHOLD, UPPER_MESSAGE_THRESHOLD)


# Set initial threshold for group
def init_group(group_id):
    if group_id not in spawn_thresholds:
        set_counters(group_id)


# Main message listener (non-command messages)
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        return

    group_id = chat.id
    init_group(group_id)

    spawn_counters[group_id] += 1

    if spawn_counters[group_id] >= RESPAWN_THRESHOLD:
        set_counters(group_id)
        await spawn_wild_pokemon(group_id, context)

    if spawn_state.get(group_id) is not None:
        return

    if spawn_counters[group_id] >= spawn_thresholds[group_id]:
        set_counters(group_id)
        await spawn_wild_pokemon(group_id, context)
    
    return True


def update_user_pokemon_db(user_id: int, pokemon_name: str):
    try:
        with SessionLocal() as session:
            new_caught_pokemon = CaughtPokemon(user_id=user_id, pokemon_name=pokemon_name)
            session.add(new_caught_pokemon)
            session.commit()
    except Exception:
        logging.error(f"Error updating user {user_id} with caught Pokémon {pokemon_name}")


async def catch_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    group_id = chat.id

    if group_id not in spawn_state:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No Pokémon has appeared yet! Keep chatting to spawn one.")
        return

    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please specify the Pokémon name to catch.")
        return

    pokemon_name = " ".join(context.args).lower()
    if pokemon_name == spawn_state[group_id].get("name", "").lower():

        # Update user profile with caught Pokémon
        user_id = update.effective_user.id
        update_user_pokemon_db(user_id, spawn_state[group_id]["name"])
        
        # Remove the spawn state for this group
        spawn_state.pop(group_id, None)

        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Congratulations! You caught {pokemon_name.capitalize()}!")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{pokemon_name.capitalize()} is not the Pokémon that appeared! Try again.")


def get_user_pokemons_db(user_id: int):
    try:
        with SessionLocal() as session:
            pokemons = session.query(CaughtPokemon).filter(CaughtPokemon.user_id == user_id).all()
            return {pokemon.pokemon_name: pokemons.count(pokemon) for pokemon in pokemons}
    except Exception:
        logging.error(f"Error retrieving Pokémon for user {user_id}")
        return {}


async def view_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    user_caught_pokemons = get_user_pokemons_db(user_id)
    if not user_caught_pokemons:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You have not caught any Pokémon yet!")
        return
    
    # Format the response
    text = ""
    for pokemon, count in user_caught_pokemons.items():
        text += f"{pokemon.capitalize()} - {count}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


if __name__ == '__main__':
    load_dotenv()  # Load environment variables from .env file
    bot_token = os.getenv('BOT_TOKEN')

    application = ApplicationBuilder().token(bot_token).build()
    
    start_handler = CommandHandler('start', start)
    catch_pokemon_handler = CommandHandler('catch', catch_pokemon)
    view_pokemon_handler = CommandHandler('mypokemon', view_pokemon)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), on_message)

    application.add_handler(start_handler)
    application.add_handler(catch_pokemon_handler)
    application.add_handler(view_pokemon_handler)
    application.add_handler(message_handler)

    application.run_polling()