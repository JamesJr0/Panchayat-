# plugins/channel.py   (new version)

from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import (
    save_file,      # automatic DB chooser  ➜ DB-1 → DB-2 → DB-3 → DB-4
    check_file,
)
import logging

logger = logging.getLogger(__name__)

media_filter = filters.document | filters.video | filters.audio


@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media_handler(bot, message):
    """Handle incoming media from the indexed channels."""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media:
            break
    else:
        return  # nothing we care about

    media.file_type = file_type
    media.caption = message.caption

    # skip duplicates that already exist in any DB
    if await check_file(media) != "okda":
        logger.info("Duplicate file skipped")
        return

    # let ia_filterdb decide which DB to use
    saved, code = await save_file(media)

    if saved and code == 1:
        logger.info("Stored %s in database", getattr(media, "file_name", "NO_FILE"))
    elif code == 0:
        logger.info("Duplicate detected while saving: %s", getattr(media, "file_name", "NO_FILE"))
    else:  # code == 2 (validation error)
        logger.warning("Validation error for: %s", getattr(media, "file_name", "NO_FILE"))
