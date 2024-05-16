from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import save_file1, save_file2, check_file

media_filter = filters.document | filters.video | filters.audio


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

    if message.id % 2 == 0:
        tru = await check_file(media)
        if tru == "okda":
            await save_file1(media)
        else:
            print("skipped duplicate file from saving to db 1 😌")
    else:
        tru = await check_file(media)
        if tru == "okda":
            await save_file2(media)
        else:
            print("skipped duplicate file from saving to db 2 😌")
