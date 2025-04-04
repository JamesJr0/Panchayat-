import re
import aiohttp
import asyncio
from io import BytesIO
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from imdb import Cinemagoer
from info import ADMINS

# Initialize Cinemagoer
ia = Cinemagoer()

# Define channel
POST_CHANNEL = -1001842826681  

def list_to_str(lst, limit=None):
    """Convert list to string, optionally limiting number of items."""
    if lst:
        return ", ".join(map(str, lst[:limit])) if limit else ", ".join(map(str, lst))
    return "N/A"

async def get_movie_details(title, year=None):
    try:
        movieid = ia.search_movie(title.lower(), results=10)
        if not movieid:
            return None
        movieid = list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], movieid))
        if not movieid:
            return None
        movieid = movieid[0].movieID

        movie = ia.get_movie(movieid)

        return {
            'title': movie.get('title'),
            'year': movie.get('year'),
            'genres': list_to_str(movie.get("genres")),
            'rating': str(movie.get("rating")),
            'runtime': list_to_str(movie.get("runtimes")),
            'cast': list_to_str(movie.get("cast"), limit=2),
            'language': list_to_str(movie.get("languages")),
            'imdb_url': f'https://www.imdb.com/title/tt{movieid}'
        }

    except Exception as e:
        print(f"Error fetching movie details: {e}")
        return None

@Client.on_message(filters.command("post"))
async def generate_post(client, message):
    if message.from_user.id not in ADMINS:
        await message.reply_text("You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please provide a movie title and optional year (e.g., /post KGF 2018)")
        return

    user_input = message.command[1:]
    year = None

    # Extract year from input
    for item in user_input:
        if item.isdigit() and len(item) == 4:
            year = item
            user_input.remove(item)
            break

    # Remove known language names
    language_keywords = ['hindi', 'tamil', 'telugu', 'malayalam', 'kannada', 'english', 'bengali']
    cleaned_input = [w for w in user_input if w.lower().strip(',') not in language_keywords]

    title = " ".join(cleaned_input)

    movie_data = await get_movie_details(title, year)

    if movie_data:
        imdb_url = movie_data["imdb_url"]
        genre = movie_data["genres"]
        runtime = movie_data["runtime"]
        rating = movie_data["rating"]
        cast = movie_data["cast"]
        language = movie_data["language"]
        year = movie_data["year"] or year

        # Deep link with title + year only
        search_query = re.sub(r'\s+', '_', f"{title} {year}").strip()

        message_text = f"""
<b>✅ {title} {year}</b>

⭐️ <b><a href="{imdb_url}">IMDB info</a></b>  
🎭 Genre: {genre}  
🗣️ Language: {language}  
⏳ Runtime: {runtime} min  
⭐ Rating: {rating}  
🎭 Cast: {cast}  
"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 Click Here To Search 🔍", url=f"http://t.me/Prosearchfatherbot?start=search_{search_query}")],
            [InlineKeyboardButton("📌 Search to ProSearchMoviez", url=f"http://t.me/ProsearchMoviez_bot?start=search_{search_query}")]
        ])

        await client.send_message(
            POST_CHANNEL, 
            message_text, 
            reply_markup=keyboard, 
            parse_mode=ParseMode.HTML, 
            disable_web_page_preview=True
        )
        await message.reply_text(f"The post for '{title} {year}' has been published!")
    else:
        await message.reply_text("Movie not found.")
