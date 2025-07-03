# database/ia_filterdb.py
# ------------------------------------------------------------
#   Multi-DB helper for Panchayath bot
#   • Four Mongo clusters (FILES_DB1-4)
#   • 7-lakh cap / DB, rollover in order
#   • Single-insert + bulk-insert API
# ------------------------------------------------------------

import asyncio
import base64
import logging
import re
from struct import pack
from typing import Dict, List, Optional, Tuple

from marshmallow.exceptions import ValidationError
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError, BulkWriteError
from umongo import Document, Instance, fields

from info import (  # loads values from your .env / info.py
    FILES_DB1,
    FILES_DB2,
    FILES_DB3,
    FILES_DB4,
    DATABASE_NAME,
    COLLECTION_NAME,
    USE_CAPTION_FILTER,
    # Removed BOT_USERNAME import
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------ #
# Mongo connections                                                        #
# ------------------------------------------------------------------------ #
def _client(uri: str) -> Tuple[AsyncIOMotorClient, AsyncIOMotorDatabase, Instance]:
    cli = AsyncIOMotorClient(uri)
    db = cli[DATABASE_NAME]
    return cli, db, Instance.from_db(db)


cli1, db1, inst1 = _client(FILES_DB1)
cli2, db2, inst2 = _client(FILES_DB2)
cli3, db3, inst3 = _client(FILES_DB3)
cli4, db4, inst4 = _client(FILES_DB4)

# ------------------------------------------------------------------------ #
# Document model factory (same structure for all DBs)                      #
# ------------------------------------------------------------------------ #
def _register(instance):
    @instance.register
    class Media(Document):
        file_id = fields.StrField(attribute="_id")
        file_ref = fields.StrField(allow_none=True)
        file_name = fields.StrField(required=True)
        file_size = fields.IntField(required=True)
        file_type = fields.StrField(allow_none=True)
        mime_type = fields.StrField(allow_none=True)
        caption = fields.StrField(allow_none=True)

        class Meta:
            indexes = ("$file_name",)
            collection_name = COLLECTION_NAME

    return Media


Media1 = _register(inst1)
Media2 = _register(inst2)
Media3 = _register(inst3)
Media4 = _register(inst4)

MEDIA_CLASSES = [Media1, Media2, Media3, Media4]

# --- User and Chat Models (IMPORTANT: Adjust collection_name if different) ---
# Assuming these user and chat collections are typically in the main database (db1)
# Adjust if your bot uses separate databases/collections for users/chats.

# Register User model with inst1 (or whichever instance manages your user collection)
@inst1.register
class User(Document):
    user_id = fields.IntField(attribute="_id")
    # Add other user fields if you have them, e.g., 'username', 'first_name', 'last_name'
    class Meta:
        collection_name = "users" # Assumed standard user collection name
        # YOU MUST VERIFY THIS MATCHES YOUR ACTUAL USER COLLECTION NAME!

# Register Chat model with inst1 (or whichever instance manages your chat collection)
@inst1.register
class Chat(Document):
    chat_id = fields.IntField(attribute="_id")
    # Add other chat fields if you have them, e.g., 'title', 'type'
    class Meta:
        collection_name = "chats" # Assumed standard chat collection name
        # YOU MUST VERIFY THIS MATCHES YOUR ACTUAL CHAT COLLECTION NAME!


# ------------------------------------------------------------------------ #
# Configuration                                                            #
# ------------------------------------------------------------------------ #
MAX_DOCS_PER_DB = 700_000          # 7 lakh

# ------------------------------------------------------------------------ #
# Utility encoders                                                         #
# ------------------------------------------------------------------------ #
def encode_file_id(b: bytes) -> str:
    r, n = b"", 0
    for i in b + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def unpack_new_file_id(new_id: str) -> Tuple[str, str]:
    d = FileId.decode(new_id)
    file_id = encode_file_id(
        pack("<iiqq", int(d.file_type), d.dc_id, d.media_id, d.access_hash)
    )
    file_ref = encode_file_ref(d.file_reference)
    return file_id, file_ref


def _norm(name: str) -> str:
    return re.sub(r"[_\-.+]", " ", str(name))


# ------------------------------------------------------------------------ #
# Internal helpers                                                         #
# ------------------------------------------------------------------------ #
async def _count(model: Document) -> int:
    try:
        return await model.collection.estimated_document_count()
    except Exception as e:
        logger.warning(f"Failed to get estimated_document_count for {model.__name__}: {e}")
        # Fallback to count_documents if estimated fails, or return 0
        return await model.collection.count_documents({})


async def _pick_model(counts: List[int]) -> Tuple[Document, int]:
    """
    Return first model whose count < cap; fallback to last.
    counts list must correspond to MEDIA_CLASSES order.
    """
    for idx, c in enumerate(counts):
        if c < MAX_DOCS_PER_DB:
            return MEDIA_CLASSES[idx], idx
    return MEDIA_CLASSES[-1], len(MEDIA_CLASSES) - 1


def _media_to_doc(media, file_id: str, file_ref: str) -> dict:
    return dict(
        _id=file_id,
        file_ref=file_ref,
        file_name=_norm(media.file_name),
        file_size=media.file_size,
        file_type=media.file_type,
        mime_type=media.mime_type,
        caption=media.caption.html if getattr(media, "caption", None) else None,
    )


# ------------------------------------------------------------------------ #
# Public single-save API                                                   #
# ------------------------------------------------------------------------ #
async def save_file(media):
    """
    Save one media object.  DB selection is automatic.

    Returns (saved: bool, code)
    code: 1 = inserted, 0 = duplicate, 2 = validation error
    """
    counts = await asyncio.gather(*[_count(m) for m in MEDIA_CLASSES])
    model, idx = await _pick_model(list(counts))
    file_id, file_ref = unpack_new_file_id(media.file_id)

    try:
        doc = model(
            file_id=file_id,
            file_ref=file_ref,
            file_name=_norm(media.file_name),
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if getattr(media, "caption", None) else None,
        )
    except ValidationError:
        return False, 2

    try:
        await doc.commit()
    except DuplicateKeyError:
        return False, 0
    return True, 1


# ------------------------------------------------------------------------ #
# NEW  bulk-save API                                                       #
# ------------------------------------------------------------------------ #
async def save_files_bulk(media_list: List) -> Dict[str, int]:
    """
    Insert many media objects with as few DB round-trips as possible.
    Returns dict  {inserted, duplicate, errors}
    """
    stats = dict(inserted=0, duplicate=0, errors=0)

    # 1) take one initial snapshot of counts
    counts = list(await asyncio.gather(*[_count(m) for m in MEDIA_CLASSES]))

    # 2) bucket documents per target model
    buckets = {m: [] for m in MEDIA_CLASSES}

    for media in media_list:
        model, idx = await _pick_model(counts)
        counts[idx] += 1  # reserve the slot
        fid, fref = unpack_new_file_id(media.file_id)

        try:
            buckets[model].append(_media_to_doc(media, fid, fref))
        except Exception:
            stats["errors"] += 1

    # 3) fire parallel insert_many
    async def _bulk(model: Document, docs: List[dict]):
        if not docs:
            return
        try:
            await model.collection.insert_many(docs, ordered=False)
            stats["inserted"] += len(docs)
        except BulkWriteError as e:
            stats["inserted"] += e.details["nInserted"]
            # duplicates → error code 11000
            dup = sum(1 for w in e.details["writeErrors"] if w["code"] == 11000)
            stats["duplicate"] += dup
            stats["errors"] += len(e.details["writeErrors"]) - dup

    await asyncio.gather(*[_bulk(m, docs) for m, docs in buckets.items()])
    return stats


# ------------------------------------------------------------------------ #
# Legacy single-DB helpers (for old code)                                  #
# ------------------------------------------------------------------------ #
async def _legacy(model, db_no: int, media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    try:
        doc = model(
            file_id=file_id,
            file_ref=file_ref,
            file_name=_norm(media.file_name),
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if getattr(media, "caption", None) else None,
        )
    except ValidationError:
        return False, 2
    try:
        await doc.commit()
    except DuplicateKeyError:
        return False, 0
    return True, 1


async def save_file1(m): return await _legacy(Media1, 1, m)
async def save_file2(m): return await _legacy(Media2, 2, m)
async def save_file3(m): return await _legacy(Media3, 3, m)
async def save_file4(m): return await _legacy(Media4, 4, m)

# ------------------------------------------------------------------------ #
# Public count functions for stats (NEW)                                   #
# ------------------------------------------------------------------------ #
async def get_files_count_db1() -> int:
    return await _count(Media1)

async def get_files_count_db2() -> int:
    return await _count(Media2)

async def get_files_count_db3() -> int:
    return await _count(Media3)

async def get_files_count_db4() -> int:
    return await _count(Media4)

async def get_total_files_count() -> int:
    counts = await asyncio.gather(*[_count(m) for m in MEDIA_CLASSES])
    return sum(counts)

async def get_users_count() -> int:
    try:
        return await User.collection.estimated_document_count()
    except Exception as e:
        logger.error(f"Error getting users count: {e}")
        return 0

async def get_chats_count() -> int:
    try:
        return await Chat.collection.estimated_document_count()
    except Exception as e:
        logger.error(f"Error getting chats count: {e}")
        return 0


# ------------------------------------------------------------------------ #
# Duplicate check (optional)                                               #
# ------------------------------------------------------------------------ #
async def check_file(media):
    fid, _ = unpack_new_file_id(media.file_id)
    for m in MEDIA_CLASSES:
        if await m.collection.find_one({"_id": fid}):
            return None
    return "okda"

# ------------------------------------------------------------------------ #
# Search & detail functions (with filter kwarg kept)                       #
# ------------------------------------------------------------------------ #
async def get_search_results(
    query: str,
    file_type: Optional[str] = None,
    max_results: int = 10,
    offset: int = 0,
    filter: bool = False,      # kept for backward compatibility
):
    query = query.strip()
    raw = (
        "."
        if not query
        else r"(\b|[\.\+\-_]|\s|&)" + query + r"(\b|[\.\+\-_]|\s|&)"
        if " " not in query
        else query.replace(" ", r".*[&\s\.\+\-_()\[\]]")
    )
    try:
        regex = re.compile(raw, flags=re.IGNORECASE)
    except re.error:
        return [], "", 0

    mongo_filter = (
        {"$or": [{"file_name": regex}, {"caption": regex}]}
        if USE_CAPTION_FILTER
        else {"file_name": regex}
    )
    if file_type:
        mongo_filter["file_type"] = file_type

    cursors = [m.find(mongo_filter).sort("$natural", -1) for m in MEDIA_CLASSES]
    offset = max(0, offset)
    per_db = await asyncio.gather(*[c.to_list(length=35) for c in cursors])

    # interleave
    inter, idx = [], [0] * len(per_db)
    while any(i < len(lst) for i, lst in zip(idx, per_db)):
        for j, lst in enumerate(per_db):
            if idx[j] < len(lst):
                inter.append(lst[idx[j]])
                idx[j] += 1

    slice_ = inter[offset : offset + max_results]
    next_off = offset + len(slice_)
    return slice_, (next_off if next_off < len(inter) else ""), len(inter)


async def get_file_details(file_id_query: str):
    f = {"file_id": file_id_query}
    for m in MEDIA_CLASSES:
        res = await m.find(f).to_list(length=1)
        if res:
            return res
    return None
