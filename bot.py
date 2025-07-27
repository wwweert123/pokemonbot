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

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

async def get_random_pokemon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pokemon = pb.pokemon(random.randint(1, 898))  # Assuming there are 898 Pokémon
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Random Pokémon: {pokemon.name.capitalize()}")

    # Send image of the Pokémon
    if pokemon.sprites.front_default:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=pokemon.sprites.front_default)

if __name__ == '__main__':
    load_dotenv()  # Load environment variables from .env file
    bot_token = os.getenv('BOT_TOKEN')

    application = ApplicationBuilder().token(bot_token).build()
    
    start_handler = CommandHandler('start', start)
    random_pokemon_handler = CommandHandler('randompokemon', get_random_pokemon)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(random_pokemon_handler)

    application.run_polling()