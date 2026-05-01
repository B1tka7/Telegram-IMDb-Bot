from config import bot, OMDB_API_KEY
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import re

non_inglish = re.compile("[^A-Za-z0-9 .,?!'\"-]")


def search_movie(title):
    url = f'https://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={title}'
    response = requests.get(url)
    data = response.json()
    if "Search" not in data:
        return None
    list_movies = data["Search"]

    kb = InlineKeyboardMarkup()

    for chapter in list_movies:
        Title = chapter["Title"]
        Year = chapter["Year"]
        imdbID = chapter["imdbID"]

        kb.add(InlineKeyboardButton(
            text=f"{Title} ({Year})",
            callback_data=f"film_{imdbID}"
        ))

    return kb


@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(
        message.chat.id,
        "I can help you find information about a movie.\n\nJust enter the movie title or use /search"
    )


@bot.message_handler(content_types=['voice', 'photo', 'video', 'audio', 'document', 'video_note', 'sticker', 'location', 'contact', 'animation', 'poll', 'dice'])
def block_non_text(msg):
    bot.reply_to(msg, "Please send text only.")


@bot.message_handler(commands=['search'])
def search_command(message):
    bot.send_message(message.chat.id, "Enter the movie title to search:")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'):
        return
    if len(message.text) > 100:
        bot.reply_to(message, "Title too long")
        return
    if non_inglish.search(message.text):
        bot.reply_to(message, "Please enter the movie title in English.")
    else:
        keyboard = search_movie(title=message.text)
        if keyboard is None:
            bot.send_message(message.chat.id, "No movies found with that title. Please try again.")
        else:
            bot.send_message(
                message.chat.id,
                "The following films have been found based on your search.",
                reply_markup=keyboard
            )


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    imdb_id = call.data.replace("film_", "")
    url_finish = f'https://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}'
    r = requests.get(url_finish, timeout=5)
    d = r.json()

    poster = d.get("Poster", "N/A")
    title = d.get("Title", "Not Found")
    year = d.get("Year", "Not Found")

    imdb_rating = (
        d.get("Ratings", [{}])[0].get("Value", "Not Found")
        if d.get("Ratings")
        else "Not Found"
    )

    rotten_tomatoes = "Not Found"
    if len(d.get("Ratings", [{}])) > 1:
        rotten_tomatoes = d.get("Ratings", [{}])[1].get("Value", "Not Found")

    length = d.get("Runtime", "Not Found")
    genre = d.get("Genre", "Not Found")
    actors = d.get("Actors", "Not Found")
    director = d.get("Director", "Not Found")
    plot = d.get("Plot", "Not Found")

    caption = (
        f"🎬 <b>{title} ({year})</b>\n\n"
        f"⭐ IMDb: <b>{imdb_rating}</b>\n"
        f"🍅 Rotten Tomatoes: <b>{rotten_tomatoes}</b>\n"
        f"⏱ Length: {length}\n"
        f"🎭 Genre: {genre}\n\n"
        f"👥 Cast: {actors}\n"
        f"🎬 Director: {director}\n\n"
        f"📖 <b>Plot:</b>\n{plot}"
    )

    if poster == "N/A":
        bot.send_message(call.message.chat.id, caption, parse_mode="HTML")
    else:
        bot.send_photo(call.message.chat.id, photo=poster, caption=caption, parse_mode="HTML")

    bot.answer_callback_query(call.id)
