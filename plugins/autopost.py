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

# Initialize IMDb API
ia = Cinemagoer()

# Define channel
POST_CHANNEL = -1001842826681  

def list_to_str(lst, limit=None):
    """Convert list to string, optionally limiting number of items."""
    if lst:
        return ", ".join(map(str, lst[:limit])) if limit else ", ".join(map(str, lst))
    return "N/A"

async def get_movie_details(title=None, year=None, imdb_id=None):
    try:
        # If IMDb link is provided
        if imdb_id:
            movie = ia.get_movie(imdb_id)
        else:
            movie_results = ia.search_movie(title.lower(), results=10)
            if not movie_results:
                return None
            
            movie_results = [m for m in movie_results if m.get('kind') in ['movie', 'tv series']]

            if not movie_results:
                return None

            # Match correct year if provided
            if year:
                matched_movies = [m for m in movie_results if str(m.get('year')) == str(year)]
                movieid = matched_movies[0].movieID if matched_movies else movie_results[0].movieID
            else:
                movieid = movie_results[0].movieID

            movie = ia.get_movie(movieid)

        return {
            'title': movie.get('title'),
            'year': movie.get('year'),
            'genres': list_to_str(movie.get("genres")),
            'rating': str(movie.get("rating")),
            'runtime': list_to_str(movie.get("runtimes")),
            'cast': list_to_str(movie.get("cast"), limit=2),
            'language': list_to_str(movie.get("languages")),
            'imdb_url': f'https://www.imdb.com/title/tt{movie.movieID}'
        }

    except Exception as e:
        print(f"Error fetching movie details: {e}")
        return None

async def send_movie_post(client, message, movie_data, is_preview=False):
    if not movie_data:
        await message.reply_text("Movie not found.")
        return

    title = movie_data["title"]
    year = movie_data["year"]
    imdb_url = movie_data["imdb_url"]
    genre = movie_data["genres"]
    runtime = movie_data["runtime"]
    rating = movie_data["rating"]
    cast = movie_data["cast"]
    language = movie_data["language"]

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
        [InlineKeyboardButton("🔎 Click Here To ProSearch 🔍", url=f"http://t.me/Prosearchfatherbot?start=search_{search_query}")],
        [InlineKeyboardButton("📌 Try ProSearchMoviez Bot", url=f"http://t.me/ProsearchMoviez_bot?start=search_{search_query}")]
    ])

    if is_preview:
        await message.reply_text(message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        await client.send_message(POST_CHANNEL, message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        await message.reply_text(f"The post for '{title} {year}' has been published!")

@Client.on_message(filters.command("post"))
async def generate_post(client, message):
    if message.from_user.id not in ADMINS:
        await message.reply_text("You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please provide a movie title, year, or IMDb link.")
        return

    user_input = message.command[1:]
    year = None
    imdb_id = None

    # If IMDb link is provided
    imdb_match = re.search(r'imdb\.com/title/tt(\d+)', " ".join(user_input))
    if imdb_match:
        imdb_id = imdb_match.group(1)
        title = None
    else:
        for item in user_input:
            if item.isdigit() and len(item) == 4:
                year = item
                user_input.remove(item)
                break

        language_keywords = ['hindi', 'tamil', 'telugu', 'malayalam', 'kannada', 'english', 'bengali']
        cleaned_input = [w for w in user_input if w.lower().strip(',') not in language_keywords]
        title = " ".join(cleaned_input)

    movie_data = await get_movie_details(title, year, imdb_id)
    await send_movie_post(client, message, movie_data, is_preview=False)

@Client.on_message(filters.command("preview"))
async def preview_post(client, message):
    if message.from_user.id not in ADMINS:
        await message.reply_text("You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please provide a movie title, year, or IMDb link.")
        return

    user_input = message.command[1:]
    year = None
    imdb_id = None

    # If IMDb link is provided
    imdb_match = re.search(r'imdb\.com/title/tt(\d+)', " ".join(user_input))
    if imdb_match:
        imdb_id = imdb_match.group(1)
        title = None
    else:
        for item in user_input:
            if item.isdigit() and len(item) == 4:
                year = item
                user_input.remove(item)
                break

        language_keywords = ['hindi', 'tamil', 'telugu', 'malayalam', 'kannada', 'english', 'bengali']
        cleaned_input = [w for w in user_input if w.lower().strip(',') not in language_keywords]
        title = " ".join(cleaned_input)

    movie_data = await get_movie_details(title, year, imdb_id)
    await send_movie_post(client, message, movie_data, is_preview=True)
