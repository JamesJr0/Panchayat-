import re
import logging
from pyrogram import Client, filters
from database.ia_filterdb import Media1, Media2, Media3, unpack_new_file_id  # Import Media3

# Define DELETE_CHANNELS 
DELETE_CHANNELS = [-1002532083098]

logger = logging.getLogger(__name__)
media_filter = filters.document | filters.video | filters.audio

# Helper function to delete from a collection
async def delete_file(collection, query):
    try:
        result = await collection.delete_many(query)
        return result.deleted_count
    except Exception as e:
        logger.error(f"Error deleting from {collection.__name__}: {e}")
        return 0

@Client.on_message(filters.chat(DELETE_CHANNELS) & media_filter)
async def delete_multiple_files(bot, message):
    """Delete multiple files from Media1, Media2, and Media3 databases and send confirmation"""

    # Determine the media type from the message
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return  # No valid media type found, exit

    # Unpack the file_id and file_ref
    file_id, file_ref = unpack_new_file_id(media.file_id)

    # Attempt to delete from Media1, Media2, Media3
    delete_results = []
    for collection in [Media1, Media2, Media3]:
        deleted_count = await delete_file(collection, {"_id": file_id})
        delete_results.append(deleted_count)

    # Check if deletion was successful in any collection
    if any(result > 0 for result in delete_results):
        logger.info(f"File with ID {file_id} successfully deleted from database.")
        await message.reply_text("Files Deleted Successfully!")
        return

    # If not found by file_id, try deleting by file_name and file_size
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    unwanted_chars = ['[', ']', '(', ')']
    for char in unwanted_chars:
        file_name = file_name.replace(char, '')

    file_name = ' '.join(filter(lambda x: not x.startswith('@'), file_name.split()))

    # Try deleting with cleaned file_name and file_size
    delete_results = []
    for collection in [Media1, Media2, Media3]:
        deleted_count = await delete_file(collection, {
            "file_name": file_name,
            "file_size": media.file_size
        })
        delete_results.append(deleted_count)

    if any(result > 0 for result in delete_results):
        logger.info(f"File '{file_name}' successfully deleted from database.")
        await message.reply_text("Files Deleted Successfully!")
        return

    # Final attempt with original file_name and file_size
    delete_results = []
    for collection in [Media1, Media2, Media3]:
        deleted_count = await delete_file(collection, {
            "file_name": media.file_name,
            "file_size": media.file_size
        })
        delete_results.append(deleted_count)

    if any(result > 0 for result in delete_results):
        logger.info(f"File '{media.file_name}' successfully deleted from database.")
        await message.reply_text("Files Deleted Successfully!")
    else:
        logger.info(f"File '{media.file_name}' not found in database.")
        await message.reply_text("File not found in database.")
