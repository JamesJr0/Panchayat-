import logging, re, base64, asyncio
from struct import pack
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client1 = AsyncIOMotorClient(DATABASE_URI1)
db1 = client1[DATABASE_NAME]
instance1 = Instance.from_db(db1)

client2 = AsyncIOMotorClient(DATABASE_URI2)
db2 = client2[DATABASE_NAME]
instance2 = Instance.from_db(db2)

client3 = AsyncIOMotorClient(DATABASE_URI3)
db3 = client3[DATABASE_NAME]
instance3 = Instance.from_db(db3)

@instance1.register
class Media1(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

@instance2.register
class Media2(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Metaa:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

@instance3.register
class Media3(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Metaa:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

async def check_file(media):
    """Check if file is present in any of the media collections"""

    # TODO: Find better way to get same file_id for the same media to avoid duplicates
    file_id, file_ref = unpack_new_file_id(media.file_id)
    
    # List of collections to check
    collections = [Media1.collection, Media2.collection, Media3.collection]
    
    # Check each collection for the file_id
    for collection in collections:
        existing_file = await collection.find_one({"_id": file_id})
        if existing_file:
            return None  # File exists in one of the collections, return early

    # If no file was found in any collection, return "okda"
    return "okda"

async def save_file1(media):
    """Save file in database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media1(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in DB 1')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in DB 1'
            )
            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to DB 1')
            return True, 1

async def save_file2(media):
    """Save file in database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media2(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in DB 2')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in DB 2'
            )
            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to DB 2')
            return True, 1

async def save_file3(media):
    """Save file in database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media3(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in DB 3')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in DB 3'
            )
            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to DB 3')
            return True, 1

async def get_search_results(query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset)"""

    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_]|\s|&)' + query + r'(\b|[\.\+\-_]|\s|&)'
    else:
        raw_pattern = query.replace(' ', r'.*[&\s\.\+\-_()\[\]]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return [], '', 0

    # Set up filter for media collections
    filter = {'$or': [{'file_name': regex}, {'caption': regex}]} if USE_CAPTION_FILTER else {'file_name': regex}
    if file_type:
        filter['file_type'] = file_type

    # Query multiple media collections asynchronously
    collections = [Media1, Media2, Media3]
    cursors = [collection.find(filter).sort('$natural', -1) for collection in collections]

    # Ensure offset is non-negative
    offset = max(offset, 0)

    # Fetch results from all collections
    files_list = await asyncio.gather(*[cursor.to_list(length=35) for cursor in cursors])

    # Interleave files from different collections
    interleaved_files = []
    indices = [0] * len(files_list)
    while any(index < len(files) for index, files in zip(indices, files_list)):
        for i, (index, files) in enumerate(zip(indices, files_list)):
            if index < len(files):
                interleaved_files.append(files[index])
                indices[i] += 1

    # Slice results based on offset and max_results
    files = interleaved_files[offset:offset + max_results]
    total_results = len(interleaved_files)

    # Calculate next offset
    next_offset = offset + len(files)

    # Return results and next offset
    return files, (next_offset if next_offset < total_results else ''), total_results

async def get_file_details(query):
    filter = {'file_id': query}
    media_collections = [Media1, Media2, Media3]

    for media in media_collections:
        cursor = media.find(filter)
        file_details = await cursor.to_list(length=1)
        if file_details:
            return file_details

    return None

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref


import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Admin User IDs
ADMIN_IDS = [6646976956]

# Languages list
LANGUAGES = ["Malayalam", "Tamil", "Telugu", "Kannada", "Hindi", "English", "Chinese", "Japanese", "Korean"]

# Store manually added movies and series
manual_titles = {
    "Movies": {},
    "Series": set()
}

async def get_latest_movies():
    latest_movies = {lang: set() for lang in LANGUAGES}
    latest_movies["Multi"] = set()  
    latest_series = set()

    # Fetch latest 20 movies from multiple databases concurrently
    movies1, movies2, movies3 = await asyncio.gather(
        Media1.collection.find().sort("$natural", -1).limit(20).to_list(None),
        Media2.collection.find().sort("$natural", -1).limit(20).to_list(None),
        Media3.collection.find().sort("$natural", -1).limit(20).to_list(None)
    )

    all_movies = movies1 + movies2 + movies3

    for movie in all_movies:
        file_name = movie.get("file_name", "").strip()
        caption = str(movie.get("caption", "")).strip()

        # Extract movie name and remove unnecessary encoding tags
        match = re.search(r"(.+?)(?:\s+(\d{4}))?(?:\.\d{3,4}p|WEB-DL|HDRip|BluRay|HEVC|AAC|DDP5.1|x264|x265|H264|H265).*", file_name, re.IGNORECASE)
        movie_name = match.group(1).strip() if match else file_name

        # Detect series (SXXEYY format)
        series_match = re.search(r"(.+?)\s?(S\d{1,2}E\d{1,2})", file_name, re.IGNORECASE)
        if series_match:
            series_name, episode_tag = series_match.groups()
            detected_languages = set(re.findall(r'\b(' + '|'.join(LANGUAGES) + r')\b', caption, re.IGNORECASE))

            if len(detected_languages) > 1:
                detected_languages = {"Multi"}

            language_tags = " ".join(f"#{lang}" for lang in detected_languages) if detected_languages else "#Unknown"
            series_title = f"{series_name} {episode_tag} {language_tags}"

            latest_series.add(series_title)
            continue  # Skip adding to movies

        # Identify and store movies based on language
        detected_languages = set(re.findall(r'\b(' + '|'.join(LANGUAGES) + r')\b', caption, re.IGNORECASE))

        for lang in detected_languages:
            latest_movies[lang].add(movie_name)

        if len(detected_languages) > 1:
            latest_movies["Multi"].add(movie_name)

    # Convert sets to lists and return structured data
    results = [{"language": lang, "movies": list(latest_movies[lang])[:8]} for lang in latest_movies if latest_movies[lang]]
    if latest_series:
        results.append({"category": "Series", "movies": list(latest_series)[:10]})

    return results



