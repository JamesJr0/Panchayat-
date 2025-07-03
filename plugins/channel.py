from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import save_file1, save_file2, save_file3, save_file4, check_file
import asyncio

media_filter = filters.document | filters.video | filters.audio

# Shared counter and lock for thread-safe updates
save_counter = 0
counter_lock = asyncio.Lock()

save_functions = [save_file1, save_file2, save_file3, save_file4]

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption

    is_new_file = await check_file(media)
    if is_new_file == "okda":
        global save_counter
        async with counter_lock:
            save_func = save_functions[save_counter % 4]
            save_counter += 1
        await save_func(media)
    else:
        print("Skipped duplicate file from saving to DB")
