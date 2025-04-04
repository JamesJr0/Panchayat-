import re
import aiohttp
import asyncio
from io import BytesIO
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from imdb import Cinemagoer
from info import ADMINS  # Importing required constants

# Initialize Cinemagoer
ia = Cinemagoer()
LONG_IMDB_DESCRIPTION = False

# Define channel
POST_CHANNEL = -1001842826681  # Replace with your actual channel ID

# Predefined genre list
KNOWN_GENRES = {
    "Action": "👊 Action", "Adventure": "🏔️ Adventure", "Animation": "🎨 Animation", "Biography": "📖 Biography", 
    "Comedy": "🤣 Comedy", "Crime": "🕵️‍♂️ Crime", "Documentary": "🎥 Documentary", "Drama": "🎭 Drama", 
    "Family": "👨‍👩‍👧 Family", "Fantasy": "🧙‍♂️ Fantasy", "Film-Noir": "🌑 Film-Noir", "History": "🏰 History", 
    "Horror": "👻 Horror", "Music": "🎵 Music", "Musical": "🎤 Musical", "Mystery": "🔍 Mystery", 
    "Romance": "🤝 Romance", "Sci-Fi": "🚀 Sci-Fi", "Sport": "⚽ Sport", "Thriller": "😱 Thriller", 
    "War": "⚔️ War", "Western": "🤠 Western"
}

def list_to_str(lst):
    if lst:
        return ", ".join(map(str, lst))
    return ""

async def get_movie_details(title, year=None):
    try:
        if year:
            movieid = ia.search_movie(f"{title.lower()} {year}", results=10)
            if movieid:
                filtered = list(filter(lambda k: str(k.get('year')) == str(year) and k.get('kind') in ['movie', 'tv series'], movieid))
                if filtered:
                    movieid = filtered[0].movieID
                else:
                    movieid = ia.search_movie(title.lower(), results=10)
                    if not movieid:
                        return None
                    movieid = list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], movieid))
                    if not movieid:
                        return None
                    movieid = movieid[0].movieID
            else:
                return None
        else:
            movieid = ia.search_movie(title.lower(), results=10)
            if not movieid:
                return None
            movieid = list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], movieid))
            if not movieid:
                return None
            movieid = movieid[0].movieID

        movie = ia.get_movie(movieid)
        date = movie.get("original air date") or movie.get("year") or "N/A"

        plot = movie.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
        else:
            plot = movie.get('plot outline')

        if plot and len(plot) > 800:
            plot = plot[:800] + "..."

        poster_url = movie.get('full-size cover url')

        return {
            'title': movie.get('title'),
            'votes': movie.get('votes'),
            "aka": list_to_str(movie.get("akas")),
            "seasons": movie.get("number of seasons"),
            "box_office": movie.get('box office'),
            'localized_title': movie.get('localized title'),
            'kind': movie.get("kind"),
            "imdb_id": f"tt{movie.get('imdbID')}",
            "cast": list_to_str(movie.get("cast")),
            "runtime": list_to_str(movie.get("runtimes")),
            "countries": list_to_str(movie.get("countries")),
            "certificates": list_to_str(movie.get("certificates")),
            "languages": list_to_str(movie.get("languages")),
            "director": list_to_str(movie.get("director")),
            "writer": list_to_str(movie.get("writer")),
            "producer": list_to_str(movie.get("producer")),
            "composer": list_to_str(movie.get("composer")),
            "cinematographer": list_to_str(movie.get("cinematographer")),
            "music_team": list_to_str(movie.get("music department")),
            "distributors": list_to_str(movie.get("distributors")),
            'release_date': date,
            'year': movie.get('year'),
            'genres': list_to_str(movie.get("genres")),
            'poster_url': poster_url,
            'plot': plot,
            'rating': str(movie.get("rating")),
            'url': f'https://www.imdb.com/title/tt{movieid}'
        }

    except Exception as e:
        print(f"An error occurred in get_movie_details: {e}")
        return None

async def fetch_imdb_details_from_cinemagoer(title, year=None):
    try:
        movie_data = await get_movie_details(title, year)
        if not movie_data:
            return None

        imdb_url = movie_data["url"]
        genre_list = movie_data["genres"].split(", ")

        filtered_genres = [KNOWN_GENRES[g] for g in genre_list if g in KNOWN_GENRES][:3]
        genre_text = " ".join(f"#{g.split(' ')[1]}" for g in filtered_genres) if filtered_genres else "N/A"

        movie_data["genre"] = genre_text
        movie_data["imdb_url"] = imdb_url
        return movie_data

    except Exception as e:
        print(f"Cinemagoer Error: {e}")
        return None

@Client.on_message(filters.command(["post", "preview"]))
async def handle_post_preview(client, message):
    is_preview = message.command[0] == "preview"
    if message.from_user.id not in ADMINS:
        await message.reply_text("You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please provide a movie title and language(s) (e.g., /post KGF 2018 English Tamil Telugu)")
        return

    user_input = message.command[1:]

    known_languages = {"arabic", "assamese", "bengali", "burmese", "chinese", "czech", "dutch", "english",
                       "filipino", "french", "german", "gujarati", "hindi", "hungarian", "indonesian",
                       "italian", "japanese", "kannada", "korean", "malay", "malayalam", "marathi",
                       "nepali", "pashto", "persian", "polish", "portuguese", "punjabi", "russian",
                       "sinhala", "spanish", "swedish", "tamil", "telugu", "thai", "turkish",
                       "ukrainian", "urdu", "vietnamese"}

    season_identifier = None
    pattern = re.compile(r"\b[Ss](\d{2})\b")

    for item in user_input:
        if pattern.match(item):
            season_identifier = item.upper()
            user_input.remove(item)
            break

    languages = []
    while user_input and user_input[-1].lower() in known_languages:
        languages.append(user_input.pop())

    languages_text = ", ".join(languages) if languages else "Unknown"

    year = None
    for item in user_input:
        if item.isdigit() and len(item) == 4:
            year = item
            user_input.remove(item)
            break

    title = " ".join(user_input)
    formatted_title = title.replace(" ", "_").replace(".", "_")

    if season_identifier:
        button_url = f"https://t.me/Prosearchfatherbot?start=search_{formatted_title}_{season_identifier}"
    else:
        button_url = f"https://t.me/Prosearchfatherbot?start=search_{formatted_title}_{year}" if year else f"https://t.me/Prosearchfatherbot?start=search_{formatted_title}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Click Here To Search 🔍", url=button_url)],
        [InlineKeyboardButton("▶️ Try Alternate Bot", url="https://t.me/ProsearchMoviez_bot")]
    ])

    movie_data = await fetch_imdb_details_from_cinemagoer(title, year)

    if movie_data:
        imdb_url = movie_data["imdb_url"]
        genre = movie_data["genre"]
        rating = movie_data.get("rating", "N/A")
        cast = movie_data.get("cast", "N/A")
        runtime = movie_data.get("runtime", "N/A")

        message_text = f"""
<b>✅ {title} {season_identifier if season_identifier else year if year else ""}</b>

<blockquote><b>🎧 {languages_text}</b></blockquote>

⭐️ <b><a href=\"{imdb_url}\">IMDB info</a></b>  
🎝 Genre: {genre}  
⏱ Runtime: <b>{runtime}</b>  
⭐ Rating: <b>{rating}</b>  
🎭 Cast: <b>{cast}</b>
"""
    else:
        message_text = f"""
<b>✅ {title} {season_identifier if season_identifier else year if year else ""}</b>

<blockquote><b>🎧 {languages_text}</b></blockquote>
"""

    if is_preview:
        await message.reply_text(
            message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    else:
        await client.send_message(
            POST_CHANNEL,
            message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        await message.reply_text(f"The post for '{title} {season_identifier if season_identifier else year if year else ''}' has been successfully published in the channel!")
