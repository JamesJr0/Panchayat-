"""
database/ia_filterdb.py   (drop-in replacement)

Features added:
- MAX_DOCS_PER_DB = 700_000  → automatic rollover DB-1 → DB-2 → DB-3 → DB-4
- New helper `save_file()` picks the target DB; the old
  `save_file1 … save_file4` remain for backward compatibility.
- `check_file`, `get_search_results`, `get_file_details` unchanged.
"""

import logging
import re
import base64
import asyncio
from struct import pack
from typing import List, Tuple, Optional

from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError

from info import (  # noqa: F401  <- pulls FILES_DBx, DATABASE_NAME, COLLECTION_NAME,
    FILES_DB1,
    FILES_DB2,
    FILES_DB3,
    FILES_DB4,
    DATABASE_NAME,
    COLLECTION_NAME,
    USE_CAPTION_FILTER,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------------
# Mongo connections (unchanged variable names)
# ------------------------------------------------------------------------------

client1 = AsyncIOMotorClient(FILES_DB1)
db1 = client1[DATABASE_NAME]
instance1 = Instance.from_db(db1)

client2 = AsyncIOMotorClient(FILES_DB2)
db2 = client2[DATABASE_NAME]
instance2 = Instance.from_db(db2)

client3 = AsyncIOMotorClient(FILES_DB3)
db3 = client3[DATABASE_NAME]
instance3 = Instance.from_db(db3)

client4 = AsyncIOMotorClient(FILES_DB4)
db4 = client4[DATABASE_NAME]
instance4 = Instance.from_db(db4)

# ------------------------------------------------------------------------------
# Document models (names and collection name kept exactly the same)
# ------------------------------------------------------------------------------

@instance1.register
class Media1(Document):
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


@instance2.register
class Media2(Document):
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


@instance3.register
class Media3(Document):
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


@instance4.register
class Media4(Document):
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


# ------------------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------------------

MEDIA_CLASSES = [Media1, Media2, Media3, Media4]
MAX_DOCS_PER_DB = 700_000  # 7-lakh threshold


async def _doc_count(model: Document) -> int:
    """Return number of documents in the collection quickly."""
    return await model.collection.estimated_document_count()


async def _select_target_model() -> Document:
    """
    Choose the MediaX class whose DB still has less than MAX_DOCS_PER_DB docs.
    Order: Media1 → Media2 → Media3 → Media4.
    If all exceed threshold, stick with the last one.
    """
    counts = await asyncio.gather(*[_doc_count(m) for m in MEDIA_CLASSES])
    for model, cnt in zip(MEDIA_CLASSES, counts):
        if cnt < MAX_DOCS_PER_DB:
            return model
    return MEDIA_CLASSES[-1]


def _normalise_file_name(file_name: str) -> str:
    return re.sub(r"(_|\-|\.|\+)", " ", str(file_name))


def _build_media_doc(media, file_id: str, file_ref: str):
    return dict(
        file_id=file_id,
        file_ref=file_ref,
        file_name=_normalise_file_name(media.file_name),
        file_size=media.file_size,
        file_type=media.file_type,
        mime_type=media.mime_type,
        caption=media.caption.html if getattr(media, "caption", None) else None,
    )


# ------------------------------------------------------------------------------
# Public helper: automatic DB-chooser
# ------------------------------------------------------------------------------

async def save_file(media):
    """
    Automatically save media in the first database that has fewer than
    MAX_DOCS_PER_DB documents.

    Returns (bool saved, int code)
    code 1 = inserted
    code 0 = duplicate
    code 2 = validation error
    """
    model = await _select_target_model()

    file_id, file_ref = unpack_new_file_id(media.file_id)

    try:
        doc = model(**_build_media_doc(media, file_id, file_ref))
    except ValidationError:
        logger.exception("Validation error while creating document")
        return False, 2

    try:
        await doc.commit()
    except DuplicateKeyError:
        logger.info("Duplicate in %s", model.__name__)
        return False, 0
    else:
        logger.info("%s saved to %s", getattr(media, "file_name", "NO_FILE"), model.__name__)
        return True, 1


# ------------------------------------------------------------------------------
# Original per-DB save functions (left intact)
# ------------------------------------------------------------------------------

async def save_file1(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    try:
        file = Media1(**_build_media_doc(media, file_id, file_ref))
    except ValidationError:
        logger.exception("Error while saving in DB 1")
        return False, 2
    try:
        await file.commit()
    except DuplicateKeyError:
        logger.warning("%s already saved in DB 1", getattr(media, "file_name", "NO_FILE"))
        return False, 0
    else:
        logger.info("%s saved to DB 1", getattr(media, "file_name", "NO_FILE"))
        return True, 1


async def save_file2(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    try:
        file = Media2(**_build_media_doc(media, file_id, file_ref))
    except ValidationError:
        logger.exception("Error while saving in DB 2")
        return False, 2
    try:
        await file.commit()
    except DuplicateKeyError:
        logger.warning("%s already saved in DB 2", getattr(media, "file_name", "NO_FILE"))
        return False, 0
    else:
        logger.info("%s saved to DB 2", getattr(media, "file_name", "NO_FILE"))
        return True, 1


async def save_file3(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    try:
        file = Media3(**_build_media_doc(media, file_id, file_ref))
    except ValidationError:
        logger.exception("Error while saving in DB 3")
        return False, 2
    try:
        await file.commit()
    except DuplicateKeyError:
        logger.warning("%s already saved in DB 3", getattr(media, "file_name", "NO_FILE"))
        return False, 0
    else:
        logger.info("%s saved to DB 3", getattr(media, "file_name", "NO_FILE"))
        return True, 1


async def save_file4(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    try:
        file = Media4(**_build_media_doc(media, file_id, file_ref))
    except ValidationError:
        logger.exception("Error while saving in DB 4")
        return False, 2
    try:
        await file.commit()
    except DuplicateKeyError:
        logger.warning("%s already saved in DB 4", getattr(media, "file_name", "NO_FILE"))
        return False, 0
    else:
        logger.info("%s saved to DB 4", getattr(media, "file_name", "NO_FILE"))
        return True, 1


# ------------------------------------------------------------------------------
# Duplicate check: unchanged
# ------------------------------------------------------------------------------

async def check_file(media):
    file_id, _ = unpack_new_file_id(media.file_id)
    for collection in [
        Media1.collection,
        Media2.collection,
        Media3.collection,
        Media4.collection,
    ]:
        if await collection.find_one({"_id": file_id}):
            return None
    return "okda"


# ------------------------------------------------------------------------------
# Search utilities (unchanged logic, just merged into this file)
# ------------------------------------------------------------------------------

async def get_search_results(
    query: str,
    file_type: Optional[str] = None,
    max_results: int = 10,
    offset: int = 0,
):
    query = query.strip()
    raw_pattern = (
        "."
        if not query
        else r"(\b|[\.\+\-_]|\s|&)"
        + query.replace(" ", r".*[&\s\.\+\-_()\[\]]")
        + r"(\b|[\.\+\-_]|\s|&)"
        if " " not in query
        else query.replace(" ", r".*[&\s\.\+\-_()\[\]]")
    )

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return [], "", 0

    mongo_filter = (
        {"$or": [{"file_name": regex}, {"caption": regex}]}
        if USE_CAPTION_FILTER
        else {"file_name": regex}
    )
    if file_type:
        mongo_filter["file_type"] = file_type

    cursors = [
        model.find(mongo_filter).sort("$natural", -1) for model in MEDIA_CLASSES
    ]
    offset = max(0, offset)

    files_per_db = await asyncio.gather(*[c.to_list(length=35) for c in cursors])

    # Interleave results
    interleaved: List[dict] = []
    idx = [0] * len(files_per_db)
    while any(i < len(lst) for i, lst in zip(idx, files_per_db)):
        for j, lst in enumerate(files_per_db):
            if idx[j] < len(lst):
                interleaved.append(lst[idx[j]])
                idx[j] += 1

    results = interleaved[offset : offset + max_results]
    next_off = offset + len(results)
    total = len(interleaved)
    return results, (next_off if next_off < total else ""), total


async def get_file_details(file_id_query: str):
    fil = {"file_id": file_id_query}
    for model in MEDIA_CLASSES:
        docs = await model.find(fil).to_list(length=1)
        if docs:
            return docs
    return None


# ------------------------------------------------------------------------------
# Utility functions (unchanged)
# ------------------------------------------------------------------------------

def encode_file_id(s: bytes) -> str:
    r, n = b"", 0
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


def unpack_new_file_id(new_file_id: str) -> Tuple[str, str]:
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash,
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
