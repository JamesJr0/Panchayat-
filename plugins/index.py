# plugins/indexer.py   ← put whatever filename you used before
#
# Fast/bulk indexer with automatic DB rollover (DB-1 → DB-4)
# ---------------------------------------------------------------------------

import re
import logging
import asyncio
from typing import Tuple, List

from pyrogram import Client, filters, enums
from pyrogram.errors import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from info import (
    ADMINS,
    CHANNELS,
    INDEX_REQ_CHANNEL as LOG_CHANNEL,
)
from utils import temp
from database.ia_filterdb import save_file, check_file   # ← auto-chooser!

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

media_filter = filters.document | filters.video | filters.audio
BATCH_SIZE = 1000                   # how many inserts to run concurrently
PROGRESS_EVERY = 5000              # update progress message every n items

# Add hard-coded admin if you had it
ADMINS = ADMINS.copy() + [567835245]

# --------------------------------------------------------------------------- #
# Helper used by ALL index-to-DBx functions                                   #
# --------------------------------------------------------------------------- #


async def _iter_media(bot: Client, chat_id: int, last_msg_id: int, start_from: int):
    """
    Async generator: yields only Message objects that contain usable media.
    """
    async for message in bot.iter_messages(chat_id, last_msg_id, start_from):
        if message.empty:
            yield "deleted", message
            continue
        if not message.media:
            yield "no_media", message
            continue
        if message.media not in (
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT,
        ):
            yield "unsupported", message
            continue

        media = getattr(message, message.media.value, None)
        if not media:
            yield "unsupported", message
            continue

        media.file_type = message.media.value
        media.caption = message.caption
        yield "media", media


async def _process_batch(batch: List, stats: dict):
    """
    Run save_file() concurrently on a batch of media objects.
    `stats` dict is mutated in-place.
    """
    async def _save(m):
        # duplicate-check inside Mongo; we call check_file only once to skip
        # obvious dups in the same batch
        saved, code = await save_file(m)
        return saved, code

    results = await asyncio.gather(*[_save(m) for m in batch])

    for saved, code in results:
        if saved:
            stats["total_files"] += 1
        elif code == 0:   # duplicate
            stats["duplicate"] += 1
        elif code == 2:   # validation error
            stats["errors"] += 1


async def _core_index(
    bot: Client,
    chat_id: int,
    last_msg_id: int,
    msg,
):
    """
    The real worker; shared by index_files_to_db1/3/4 and index_files_to_db.
    """
    stats = dict(
        total_files=0,
        duplicate=0,
        errors=0,
        deleted=0,
        no_media=0,
        unsupported=0,
    )
    batch = []
    current = temp.CURRENT
    temp.CANCEL = False

    async for kind, item in _iter_media(bot, chat_id, last_msg_id, temp.CURRENT):
        if temp.CANCEL:
            break

        current += 1
        if current % PROGRESS_EVERY == 0:
            await msg.edit_text(
                text=(
                    f"Fetched: <code>{current}</code>\n"
                    f"Saved: <code>{stats['total_files']}</code>\n"
                    f"Duplicates: <code>{stats['duplicate']}</code>\n"
                    f"Deleted: <code>{stats['deleted']}</code>\n"
                    f"Non-Media: <code>{stats['no_media'] + stats['unsupported']}</code>"
                    f" (Unsupported: <code>{stats['unsupported']}</code>)\n"
                    f"Errors: <code>{stats['errors']}</code>"
                ),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Cancel", callback_data="index_cancel")]]
                ),
            )

        if kind == "deleted":
            stats["deleted"] += 1
        elif kind == "no_media":
            stats["no_media"] += 1
        elif kind == "unsupported":
            stats["unsupported"] += 1
        elif kind == "media":
            # optional cheap duplicate skip before hitting DB
            if await check_file(item) != "okda":
                stats["duplicate"] += 1
                continue
            batch.append(item)
            # process when batch is full
            if len(batch) >= BATCH_SIZE:
                await _process_batch(batch, stats)
                batch.clear()

    # final leftovers
    if batch:
        await _process_batch(batch, stats)

    return stats


# --------------------------------------------------------------------------- #
# Callback-query / command handlers remain mostly unchanged                   #
# but call _core_index() to do the heavy work                                 #
# --------------------------------------------------------------------------- #

# … the giant on_callback_query handler (index_files) in your original code …
#     stays exactly the same EXCEPT that each branch now calls:
#
#         await index_files_to_db1(last_msg_id, chat_id, msg, bot)
#
# etc.  Those wrappers have been rewritten below.

# ---------------- simple wrappers ---------------- #


async def index_files_to_db1(lst_msg_id, chat, msg, bot):
    stats = await _core_index(bot, chat, lst_msg_id, msg)
    await msg.edit(
        "Successfully saved <code>{total_files}</code> files!\n"
        "Duplicates: <code>{duplicate}</code>\n"
        "Deleted: <code>{deleted}</code>\n"
        "Non-Media: <code>{non_media}</code>\n"
        "Errors: <code>{errors}</code>".format(
            total_files=stats["total_files"],
            duplicate=stats["duplicate"],
            deleted=stats["deleted"],
            non_media=stats["no_media"] + stats["unsupported"],
            errors=stats["errors"],
        )
    )


# DB-3 and DB-4 wrappers kept for compatibility, they call the same core worker.
# They exist only because the buttons in your UI still reference them.

async def index_files_to_db3(lst_msg_id, chat, msg, bot):
    await index_files_to_db1(lst_msg_id, chat, msg, bot)  # same logic


async def index_files_to_db4(lst_msg_id, chat, msg, bot):
    await index_files_to_db1(lst_msg_id, chat, msg, bot)  # same logic


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    # “Index to All DBs” now simply calls the same core; the automatic DB
    # chooser inside save_file() will scatter inserts across DB-1…4 anyway.
    await index_files_to_db1(lst_msg_id, chat, msg, bot)


# --------------------------------------------------------------------------- #
# Real-time channel-media listener                                            #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def live_media(bot, message):
    """Instantly index new posts from the watched CHANNELS."""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption

    if await check_file(media) != "okda":
        logger.info("Duplicate live media skipped")
        return

    saved, code = await save_file(media)
    if saved:
        logger.info("Live media saved in DB")
    elif code == 0:
        logger.info("Duplicate detected on commit (live)")
    else:
        logger.warning("Validation error on live media")
