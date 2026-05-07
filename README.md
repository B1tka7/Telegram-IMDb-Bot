# IMDb Telegram Bot

## Version
v1.1

## Features
- Movie search via OMDb API
- Inline results
- Movie details (IMDb, Rotten Tomatoes, cast, etc.)
- Wishlist (SQLite)
- Mark as watched/unwatched
- Delete from wishlist

## How to run

    Install dependencies:

pip install -r requirements.txt

    Create a .env file:

BOT_TOKEN=your_new_token
OMDB_API_KEY=your_api_key

    Start the bot:

python main.py

## Updates (v1.1)
- Added personal wishlist system
- Added SQLite database
- Added status tracking (watched / not watched)
- Improved inline UX
