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

# filters
non_english = re.compile("[^A-Za-z0-9 .,?!'\"-]")


# =========================
# API
# =========================

def search_movies(title):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={title}"
    return requests.get(url).json()

def get_movie(imdb_id):
    url = f"https://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}"
    return requests.get(url).json()


# =========================
# REGISTER
# =========================

def register_handlers(bot):

    # START
    @bot.message_handler(commands=['start'])
    def start(message):
        bot.send_message(
            message.chat.id,
            "<b>Movie Bot</b>\n\n"
            "Search movies with /search or just type name\n"
            "Wishlist: /wishlist\n",
            parse_mode="HTML"
        )

    # SEARCH COMMAND
    @bot.message_handler(commands=['search'])
    def search_cmd(message):
        bot.send_message(message.chat.id, "🔎 Enter movie title:")

    # TEXT SEARCH
    @bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
    def handle_text(message):

        if len(message.text) > 100:
            bot.reply_to(message, "Title too long")
            return

        if non_english.search(message.text):
            bot.reply_to(message, "English only")
            return

        data = search_movies(message.text)

        if "Search" not in data:
            bot.send_message(message.chat.id, "No results found")
            return

        kb = types.InlineKeyboardMarkup()

        for m in data["Search"]:
            kb.add(
                types.InlineKeyboardButton(
                    text=f"{m['Title']} ({m['Year']})",
                    callback_data=f"film_{m['imdbID']}"
                )
            )

        bot.send_message(message.chat.id, "Results:", reply_markup=kb)


    # =========================
    # MOVIE DETAILS
    # =========================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("film_"))
    def film(call):
        imdb_id = call.data.replace("film_", "")
        d = get_movie(imdb_id)

        poster = d.get("Poster", "N/A")
        title = d.get("Title", "Not Found")
        year = d.get("Year", "Not Found")
        imdb_rating = d.get("imdbRating", "Not Found")
        genre = d.get("Genre", "Not Found")
        actors = d.get("Actors", "Not Found")
        director = d.get("Director", "Not Found")
        plot = d.get("Plot", "Not Found")

        text = (
            f"🎬 <b>{title} ({year})</b>\n\n"
            f"⭐ IMDb: <b>{imdb_rating}</b>\n"
            f"🎭 Genre: {genre}\n\n"
            f"👥 Actors: {actors}\n"
            f"🎬 Director: {director}\n\n"
            f"📖 <b>Plot:</b>\n{plot}"
        )

        kb = types.InlineKeyboardMarkup()

        kb.add(types.InlineKeyboardButton("Add to wishlist", callback_data=f"add|{imdb_id}"))

        bot.answer_callback_query(call.id)

        if poster != "N/A":
            bot.send_photo(call.message.chat.id, poster, caption=text, parse_mode="HTML", reply_markup=kb)
        else:
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)


    # =========================
    # ADD TO WISHLIST
    # =========================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("add|"))
    def add(call):
        user_id = call.from_user.id
        imdb_id = call.data.split("|")[1]

        c.execute("SELECT * FROM movie_list WHERE imdb_id=? AND user_id=?", (imdb_id, user_id))
        if c.fetchone():
            bot.answer_callback_query(call.id, "Already in wishlist")
            return

        movie = get_movie(imdb_id)

        c.execute(
            "INSERT INTO movie_list VALUES (?, ?, ?, ?, ?)",
            (movie["Title"], movie["Year"], False, imdb_id, user_id)
        )
        db.commit()

        bot.answer_callback_query(call.id, "Added to wishlist")


    # =========================
    # WISHLIST
    # =========================
    @bot.message_handler(commands=['wishlist'])
    def wishlist(message):
        user_id = message.from_user.id

        c.execute("SELECT title, year, status, imdb_id FROM movie_list WHERE user_id=?", (user_id,))
        rows = c.fetchall()

        if not rows:
            bot.send_message(message.chat.id, "Wishlist empty")
            return

        for title, year, status, imdb_id in rows:

            status_text = "Watched" if status else "Not watched"

            text = f"<b>{title}</b> ({year})\n<i>{status_text}</i>"

            kb = types.InlineKeyboardMarkup()

            kb.add(
                types.InlineKeyboardButton("Delete", callback_data=f"delete|{imdb_id}"),
                types.InlineKeyboardButton("Details", callback_data=f"film_{imdb_id}")
            )

            kb.add(
                types.InlineKeyboardButton(
                    "✔ Mark watched" if not status else "↩ Mark not watched",
                    callback_data=f"toggle|{imdb_id}"
                )
            )

            bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=kb)


    # =========================
    # DELETE
    # =========================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete|"))
    def delete(call):
        imdb_id = call.data.split("|")[1]
        user_id = call.from_user.id

        c.execute("DELETE FROM movie_list WHERE imdb_id=? AND user_id=?", (imdb_id, user_id))
        db.commit()

        bot.answer_callback_query(call.id, "Deleted")


    # =========================
    # TOGGLE WATCHED
    # =========================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("toggle|"))
    def toggle(call):
        imdb_id = call.data.split("|")[1]
        user_id = call.from_user.id

        c.execute("SELECT status FROM movie_list WHERE imdb_id=? AND user_id=?", (imdb_id, user_id))
        row = c.fetchone()

        if not row:
            return

        new_status = not row[0]

        c.execute(
            "UPDATE movie_list SET status=? WHERE imdb_id=? AND user_id=?",
            (new_status, imdb_id, user_id)
        )
        db.commit()

        bot.answer_callback_query(call.id, "Updated")
