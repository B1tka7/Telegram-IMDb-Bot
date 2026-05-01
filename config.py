import os
from dotenv import load_dotenv
import telebot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
