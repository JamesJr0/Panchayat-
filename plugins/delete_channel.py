import re
import logging
from pyrogram import Client, filters
from database.ia_filterdb import Media1, Media2, Media3, Media4, unpack_new_file_id

# Define DELETE_CHANNELS 
DELETE_CHANNELS = [-1002532083098]

logger = logging.getLogger(__name__)
media_filter = filters.document | filters.video | filters.audio

@Client.on_message(filters.chat(DELETE_CHANNELS) & media_filter)
async def delete_multiple_files(bot, message):
    """Delete multiple files from Media1, Media2, Media3 and Media4 databases and send confirmation"""

    # Determine the media type from the message
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return  # No valid media type found, exit

    # Unpack the file_id and file_ref
    file_id, file_ref = unpack_new_file_id(media.file_id)

    # Attempt to delete from all three collections
    result_media1 = await Media1.collection.delete_one({"_id": file_id})
    result_media2 = await Media2.collection.delete_one({"_id": file_id}) if not result_media1.deleted_count else None
    result_media3 = await Media3.collection.delete_one({"_id": file_id}) if not (result_media1.deleted_count or (result_media2 and result_media2.deleted_count)) else None
    result_media4 = await Media4.collection.delete_one({"_id": file_id}) if not (result_media1.deleted_count or (result_media2 and result_media2.deleted_count)) or (result_media3 and result_media3.deleted_count) else None

    if result_media1.deleted_count or (result_media2 and result_media2.deleted_count) or (result_media3 and result_media3.deleted_count) or (result_media4 and result_media4.deleted_count):
        logger.info(f"File with ID {file_id} successfully deleted from database.")
        await message.reply_text("Files Deleted Successfully!")
    else:
        # If not found by file_id, try deleting by file_name and file_size
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        unwanted_chars = ['[', ']', '(', ')']
        for char in unwanted_chars:
            file_name = file_name.replace(char, '')

        # Clean file_name by removing words starting with '@'
        file_name = ' '.join(filter(lambda x: not x.startswith('@'), file_name.split()))

        # Try deleting from all three collections with cleaned file_name and file_size
        result_media1 = await Media1.collection.delete_many({
            "file_name": file_name,
            "file_size": media.file_size
        })
        result_media2 = await Media2.collection.delete_many({
            "file_name": file_name,
            "file_size": media.file_size
        }) if not result_media1.deleted_count else None
        result_media3 = await Media3.collection.delete_many({
            "file_name": file_name,
            "file_size": media.file_size
        }) if not (result_media1.deleted_count or (result_media2 and result_media2.deleted_count)) else None
        result_media4 = await Media4.collection.delete_many({
            "file_name": file_name,
            "file_size": media.file_size
        }) if not (result_media1.deleted_count or (result_media2 and result_media2.deleted_count) or (result_media3 and result_media3.deleted_count)) else None
        if result_media1.deleted_count or (result_media2 and result_media2.deleted_count) or (result_media3 and result_media3.deleted_count):
            logger.info(f"File '{file_name}' successfully deleted from database.")
            await message.reply_text("Files Deleted Successfully!")
        else:
            # Final attempt with original file_name and file_size
            result_media1 = await Media1.collection.delete_many({
                "file_name": media.file_name,
                "file_size": media.file_size
            })
            result_media2 = await Media2.collection.delete_many({
                "file_name": media.file_name,
                "file_size": media.file_size
            }) if not result_media1.deleted_count else None
            result_media3 = await Media3.collection.delete_many({
                "file_name": media.file_name,
                "file_size": media.file_size
            }) if not (result_media1.deleted_count or (result_media2 and result_media2.deleted_count)) else None
            result_media4 = await Media4.collection.delete_many({
                "file_name": media.file_name,
                "file_size": media.file_size
            }) if not (result_media1.deleted_count or (result_media2 and result_media2.deleted_count), (result_media3 and result_media3.deleted_count)) else None

            if result_media1.deleted_count or (result_media2 and result_media2.deleted_count) or (result_media3 and result_media3.deleted_count) or (result_media4 and result_media4.deleted_count):
                logger.info(f"File '{media.file_name}' successfully deleted from database.")
                await message.reply_text("Files Deleted Successfully!")
            else:
                logger.info(f"File '{media.file_name}' not found in database.")
                await message.reply_text("File not found in database.")
