import re
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from bs4 import BeautifulSoup
from info import ADMINS  # Only importing ADMINS

# Define channel and API key here
POST_CHANNEL = -1001842826681  # Replace with your actual channel ID
OMDB_API_KEY = "544664d"  # Replace with your actual OMDb API key

# Predefined genre list
KNOWN_GENRES = {
    "Action": "👊 Action", "Adventure": "🏔️ Adventure", "Animation": "🎨 Animation", "Biography": "📖 Biography", 
    "Comedy": "🤣 Comedy", "Crime": "🕵️‍♂️ Crime", "Documentary": "🎥 Documentary", "Drama": "🎭 Drama", 
    "Family": "👨‍👩‍👧 Family", "Fantasy": "🧚‍♂️ Fantasy", "Film-Noir": "🌑 Film-Noir", "History": "🏰 History", 
    "Horror": "👻 Horror", "Music": "🎵 Music", "Musical": "🎤 Musical", "Mystery": "🔍 Mystery", 
    "Romance": "💕 Romance", "Sci-Fi": "🚀 Sci-Fi", "Sport": "⚽ Sport", "Thriller": "😱 Thriller", 
    "War": "⚔️ War", "Western": "🤠 Western"
}

def fetch_imdb_details_from_omdb(title):
    """Fetch IMDb data from OMDb API."""
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if "Response" in data and data["Response"] == "False":
            return None

        imdb_id = data.get("imdbID", None)
        genre_list = data.get("Genre", "").split(", ")

        # Filter genres and limit to 3
        filtered_genres = [KNOWN_GENRES[g] for g in genre_list if g in KNOWN_GENRES][:3]
        genre_text = " ".join(f"#{g.split(' ')[1]}" for g in filtered_genres) if filtered_genres else "N/A"

        return {
            "imdb_url": f"https://www.imdb.com/title/{imdb_id}" if imdb_id else None,
            "genre": genre_text
        }

    except Exception as e:
        print(f"OMDb API Error: {e}")
        return None

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

    # Detect series identifier (S01, S02, etc.)
    season_identifier = None
    pattern = re.compile(r"\b[Ss](\d{2})\b")

    for item in user_input:
        if pattern.match(item):
            season_identifier = item.upper()
            user_input.remove(item)
            break

    # Extract languages
    languages = []
    while user_input and user_input[-1].lower() in known_languages:
        languages.append(user_input.pop())

    languages_text = ", ".join(languages) if languages else "Unknown"

    # Extract year
    year = None
    for item in user_input:
        if item.isdigit() and len(item) == 4:
            year = item
            user_input.remove(item)
            break

    title = " ".join(user_input)

    # Format button URL (Movie or Series)
    formatted_title = title.replace(" ", "_").replace(".", "_")
    
    if season_identifier:
        button_url = f"http://t.me/prosearchfatherbot?start=search_{formatted_title}_{season_identifier}"
    else:
        button_url = f"http://t.me/prosearchfatherbot?start=search_{formatted_title}_{year}" if year else f"http://t.me/prosearchfatherbot?start=search_{formatted_title}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Click Here To Search 🔍", url=button_url)]
    ])

    # Fetch IMDb data from OMDb
    movie_data = fetch_imdb_details_from_omdb(title)

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
        # If IMDb details are unavailable, post without them
        message_text = f"""
<b>✅ {title} {season_identifier if season_identifier else year if year else ""}</b>

<blockquote><b>🎙 {languages_text}</b></blockquote>
"""

    # Send post
    await client.send_message(
    POST_CHANNEL, 
    message_text, 
    reply_markup=keyboard, 
    parse_mode=ParseMode.HTML, 
    disable_web_page_preview=True  # Disables link previews
    )
    await message.reply_text(f"The post for '{title} {season_identifier if season_identifier else year if year else ''}' has been successfully published in the channel!")
