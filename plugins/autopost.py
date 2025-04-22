import re
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from imdb import Cinemagoer
from info import CHANNELS, ADMINS, LOG_CHANNEL
from database.ia_filterdb import save_file, unpack_new_file_id
from utils import temp
from database.users_chats_db import db

# Initialize Cinemagoer
ia = Cinemagoer()
LONG_IMDB_DESCRIPTION = False

# Define channel
POST_CHANNEL = -1001842826681

# Predefined genre list
KNOWN_GENRES = {
    "Action": "👊 Action", "Adventure": "🏔️ Adventure", "Animation": "🎨 Animation", "Biography": "📖 Biography",
    "Comedy": "🤣 Comedy", "Crime": "🕵️‍♂️ Crime", "Documentary": "🎥 Documentary", "Drama": "🎭 Drama",
    "Family": "👨‍👩‍👧 Family", "Fantasy": "🧚‍♂️ Fantasy", "Film-Noir": "🌑 Film-Noir", "History": "🏰 History",
    "Horror": "👻 Horror", "Music": "🎵 Music", "Musical": "🎤 Musical", "Mystery": "🔍 Mystery",
    "Romance": "💕 Romance", "Sci-Fi": "🚀 Sci-Fi", "Sport": "⚽ Sport", "Thriller": "😱 Thriller",
    "War": "⚔️ War", "Western": "🤠 Western"
}

processed_movies = set()
media_filter = filters.document | filters.video

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
        if movie.get("original air date"):
            date = movie["original air date"]
        elif movie.get("year"):
            date = movie.get("year")
        else:
            date = "N/A"

        plot = movie.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
        else:
            plot = movie.get('plot outline')

        if plot and len(plot) > 800:
            plot = plot[:800] + "..."

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
        return {
            "imdb_url": imdb_url,
            "genre": genre_text
        }
    except Exception as e:
        print(f"Cinemagoer Error: {e}")
        return None

async def movie_name_format(file_name):
    filename = re.sub(r'http\S+', '', re.sub(r'@\w+|#\w+', '', file_name).replace('_', ' ').replace('[', '').replace(']', '').replace('(', '').replace(')', '').replace('{', '').replace('}', '').replace('.', ' ').replace('@', '').replace(':', '').replace(';', '').replace("'", '').replace('-', '').replace('!', '')).strip()
    return filename

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    bot_id = bot.me.id
    media = getattr(message, message.media.value, None)
    if media.mime_type in ['video/mp4', 'video/x-matroska']:
        media.file_type = message.media.value
        media.caption = message.caption
        success_sts = await save_file(media)
        if success_sts == 'suc':
            file_id, file_ref = unpack_new_file_id(media.file_id)
            await send_movie_updates(bot, file_name=media.file_name, caption=media.caption, file_id=file_id)

async def send_movie_updates(bot, file_name, caption, file_id):
    try:
        year_match = re.search(r"\b(19|20)\d{2}\b", caption)
        year = year_match.group(0) if year_match else None
        pattern = r"(?i)(?:s|season)0*(\d{1,2})"
        season = re.search(pattern, caption)
        if not season:
            season = re.search(pattern, file_name)
        if year:
            file_name = file_name[:file_name.find(year) + 4]
        if not year and season:
            season = season.group(1) if season else None
            file_name = file_name[:file_name.find(season) + 1]
        language = ""
        nb_languages = ["Hindi", "Bengali", "English", "Marathi", "Tamil", "Telugu", "Malayalam", "Kannada", "Punjabi", "Gujrati", "Korean", "Japanese", "Bhojpuri", "Dual", "Multi"]
        for lang in nb_languages:
            if lang.lower() in caption.lower():
                language += f"{lang}, "
        language = language.strip(", ") or "Unknown"
        movie_name = await movie_name_format(file_name)
        if movie_name in processed_movies:
            return
        processed_movies.add(movie_name)
        season_identifier = f"S{season.zfill(2)}" if season else None
        formatted_title = movie_name.replace(" ", "_").replace(".", "_")
        if season_identifier:
            button1_url = f"http://t.me/Prosearchfatherbot?start=search_{formatted_title}_{season_identifier}"
            button2_url = f"http://t.me/ProSearchPro_Bot?start=search_{formatted_title}_{season_identifier}"
        else:
            button1_url = f"http://t.me/Prosearchfatherbot?start=search_{formatted_title}"
            button2_url = f"http://t.me/ProSearchPro_Bot?start=search_{formatted_title}"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🥀 Pro Search 🌼", url=button1_url),
                InlineKeyboardButton("🌿 Go Search🌸", url=button2_url)
            ],
            [InlineKeyboardButton("🤖 BOT UPDATES 🤖", url="https://t.me/+p0RB9_pSWnU2Nzll")]
        ])
        movie_data = await fetch_imdb_details_from_cinemagoer(movie_name, year)
        if movie_data:
            imdb_url = movie_data["imdb_url"]
            genre = movie_data["genre"]
            message_text = f"""
<b>✅ {movie_name} {season_identifier if season_identifier else year if year else ""}</b>

<b><blockquote>🎙 {language}</blockquote></b>

⭐️ <b><a href="{imdb_url}">IMDB info</a></b>
📽 Genre: {genre}
"""
        else:
            message_text = f"""
<b>✅ {movie_name} {season_identifier if season_identifier else year if year else ""}</b>

<blockquote><b>🎙 {language}</b></blockquote>
"""
        await bot.send_message(
            POST_CHANNEL,
            message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f'Failed to send movie update. Error - {e}')
        await bot.send_message(LOG_CHANNEL, f'Failed to send movie update. Error - {e}')

@Client.on_message(filters.command("post"))
async def generate_post(client, message):
    if message.from_user.id not in ADMINS:
        await message.reply_text("You are not authorized to use this command.")
        return
    if len(message.command) < 2:
        await message.reply_text("Please provide a movie title and language(s) (e.g., /post KGF 2018 English Tamil Telugu)")
        return
    user_input = message.command[1:]
    known_languages = {
        "arabic", "assamese", "bengali", "burmese", "chinese", "czech", "dutch", "english",
        "filipino", "french", "german", "gujarati", "hindi", "hungarian", "indonesian",
        "italian", "japanese", "kannada", "korean", "malay", "malayalam", "marathi",
        "nepali", "pashto", "persian", "polish", "portuguese", "punjabi", "russian",
        "sinhala", "spanish", "swedish", "tamil", "telugu", "thai", "turkish",
        "ukrainian", "urdu", "vietnamese"
    }
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
        button1_url = f"http://t.me/Prosearchfatherbot?start=search_{formatted_title}_{season_identifier}"
        button2_url = f"http://t.me/ProSearchPro_Bot?start=search_{formatted_title}_{season_identifier}"
    else:
        button1_url = f"http://t.me/Prosearchfatherbot?start=search_{formatted_title}_{year}" if year else f"http://t.me/Prosearchfatherbot?start=search_{formatted_title}"
        button2_url = f"http://t.me/ProSearchPro_Bot?start=search_{formatted_title}_{year}" if year else f"http://t.me/ProSearchPro_Bot?start=search_{formatted_title}"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🥀 Pro Search 🌼", url=button1_url),
            InlineKeyboardButton("🌿 Go Search🌸", url=button2_url)
        ],
        [InlineKeyboardButton("🤖 BOT UPDATES 🤖", url="https://t.me/+p0RB9_pSWnU2Nzll")]
    ])
    movie_data = await fetch_imdb_details_from_cinemagoer(title, year)
    if movie_data:
        imdb_url = movie_data["imdb_url"]
        genre = movie_data["genre"]
        message_text = f"""
<b>✅ {title} {season_identifier if season_identifier else year if year else ""}</b>

<b><blockquote>🎙 {languages_text}</blockquote></b>

⭐️ <b><a href="{imdb_url}">IMDB info</a></b>
📽 Genre: {genre}
"""
    else:
        message_text = f"""
<b>✅ {title} {season_identifier if season_identifier else year if year else ""}</b>

<blockquote><b>🎙 {languages_text}</b></blockquote>
"""
    await client.send_message(
        POST_CHANNEL,
        message_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    await message.reply_text(f"The post for '{title} {season_identifier if season_identifier else year if year else ''}' has been successfully published in the channel!")
