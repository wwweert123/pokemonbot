import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

import pokebase as pb

import os
from dotenv import load_dotenv

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a pokemon bot! Use /help to see available commands.")

async def get_random_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pokemon = pb.pokemon(random.randint(1, 898))  # Assuming there are 898 Pokémon
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Random Pokémon: {pokemon.name.capitalize()}")

    print(f"Random Pokémon: {pokemon.name}")

    # Send image of the Pokémon
    if pokemon.sprites.front_default:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=pokemon.sprites.front_default)

spawn_counters = {}       # group_id -> int
spawn_thresholds = {}     # group_id -> int

# Set initial threshold for group
def init_group(group_id):
    if group_id not in spawn_thresholds:
        spawn_thresholds[group_id] = random.randint(5, 15)
        spawn_counters[group_id] = 0

# Main message listener (non-command messages)
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    print(chat.type, chat.id)

    if chat.type not in ["group", "supergroup"]:
        return

    group_id = chat.id
    init_group(group_id)

    # if not spawn_state["caught"]:  # Only spawn if nothing is active
    #     return

    spawn_counters[group_id] += 1

    print(spawn_counters[group_id], spawn_thresholds[group_id])

    if spawn_counters[group_id] >= spawn_thresholds[group_id]:
        # Reset the counters
        spawn_counters[group_id] = 0
        spawn_thresholds[group_id] = random.randint(5, 15)

        # pokemon = random.choice(POKEMONS)
        # spawn_state["name"] = pokemon
        # spawn_state["caught"] = False

        pokemon = pb.pokemon(random.randint(1, 898))  # Assuming there are 898 Pokémon
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Random Pokémon: {pokemon.name.capitalize()}")

        # Send image of the Pokémon
        if pokemon.sprites.front_default:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=pokemon.sprites.front_default)

        await context.bot.send_message(chat_id=group_id, text="👀 A wild Pokémon has appeared! Use /catch <name> to catch it!")


if __name__ == '__main__':
    load_dotenv()  # Load environment variables from .env file
    bot_token = os.getenv('BOT_TOKEN')

    application = ApplicationBuilder().token(bot_token).build()
    
    start_handler = CommandHandler('start', start)
    random_pokemon_handler = CommandHandler('randompokemon', get_random_pokemon)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), on_message)

    application.add_handler(start_handler)
    application.add_handler(random_pokemon_handler)
    application.add_handler(message_handler)

    application.run_polling()