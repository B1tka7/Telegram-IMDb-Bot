import re
import requests
import sqlite3
import telebot
from telebot import types
from config import OMDB_API_KEY

# DB
db = sqlite3.connect('example.db', check_same_thread=False)
c = db.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS movie_list (
    title text,
    year text,
    status boolean,
    imdb_id text,
    user_id integer
)
""")
db.commit()

non_english = re.compile("[^A-Za-z0-9 .,?!'\"-]")

# SEARCH
def search_movies(title):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={title}"
    return requests.get(url).json()

def get_movie(imdb_id):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}"
    return requests.get(url).json()

def register_handlers(bot):

    @bot.message_handler(commands=['start'])
    def start(message):
        bot.send_message(
            message.chat.id,
            "Movie bot ready.\n/search or type a title\n/wishlist"
        )

    @bot.message_handler(commands=['search'])
    def search_cmd(message):
        bot.send_message(message.chat.id, "Enter movie title:")

    @bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
    def handle_text(message):

        if len(message.text) > 100:
            bot.reply_to(message, "Too long")
            return

        if non_english.search(message.text):
            bot.reply_to(message, "English only")
            return

        data = search_movies(message.text)

        if "Search" not in data:
            bot.send_message(message.chat.id, "No results")
            return

        kb = types.InlineKeyboardMarkup()

        for m in data["Search"]:
            kb.add(types.InlineKeyboardButton(
                text=f"{m['Title']} ({m['Year']})",
                callback_data=f"film_{m['imdbID']}"
            ))

        bot.send_message(message.chat.id, "Results:", reply_markup=kb)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("film_"))
    def film(call):
        imdb_id = call.data.replace("film_", "")
        data = get_movie(imdb_id)

        text = (
            f"<b>{data['Title']}</b> ({data['Year']})\n\n"
            f"Genre: {data.get('Genre')}\n"
            f"Actors: {data.get('Actors')}\n\n"
            f"Plot:\n{data.get('Plot')}"
        )

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Add to wishlist", callback_data=f"add|{imdb_id}"))

        if data.get("Poster") and data["Poster"] != "N/A":
            bot.send_photo(call.message.chat.id, data["Poster"], caption=text, parse_mode="HTML", reply_markup=kb)
        else:
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("add|"))
    def add(call):
        user_id = call.from_user.id
        imdb_id = call.data.split("|")[1]

        c.execute("SELECT * FROM movie_list WHERE imdb_id=? AND user_id=?", (imdb_id, user_id))
        if c.fetchone():
            bot.answer_callback_query(call.id, "Already added")
            return

        movie = get_movie(imdb_id)

        c.execute(
            "INSERT INTO movie_list VALUES (?, ?, ?, ?, ?)",
            (movie["Title"], movie["Year"], False, imdb_id, user_id)
        )
        db.commit()

        bot.answer_callback_query(call.id, "Added")

    @bot.message_handler(commands=['wishlist'])
    def wishlist(message):
        user_id = message.from_user.id

        c.execute("SELECT title, year, status, imdb_id FROM movie_list WHERE user_id=?", (user_id,))
        rows = c.fetchall()

        if not rows:
            bot.send_message(message.chat.id, "Empty wishlist")
            return

        for title, year, status, imdb_id in rows:

            text = f"<b>{title}</b> ({year})\n" + ("Watched" if status else "Not watched")

            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Delete", callback_data=f"delete|{imdb_id}"))

            bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=kb)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete|"))
    def delete(call):
        imdb_id = call.data.split("|")[1]
        user_id = call.from_user.id

        c.execute("DELETE FROM movie_list WHERE imdb_id=? AND user_id=?", (imdb_id, user_id))
        db.commit()

        bot.answer_callback_query(call.id, "Deleted")
