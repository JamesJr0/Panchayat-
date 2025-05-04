from pyrogram import Client, filters
import datetime
import asyncio
from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages

@Client.on_message(filters.command("skipbroadcast") & filters.user(ADMINS) & filters.reply)
async def skip_broadcast(bot, message):
    # Parse the skip number from the command
    try:
        skip = int(message.command[1])
    except (IndexError, ValueError):
        return await message.reply_text("Usage: /skipbroadcast <number> (as reply to message)")

    users = await db.get_all_users()  # Should be an async generator or list
    b_msg = message.reply_to_message
    sts = await message.reply_text(
        f"Broadcasting your message...\nSkipped: {skip} users."
    )

    start_time = datetime.datetime.now()
    total_users = await db.total_users_count()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0

    idx = 0
    async for user in users:
        if idx < skip:
            idx += 1
            continue

        try:
            pti, sh = await broadcast_messages(int(user['id']), b_msg)
            if pti:
                success += 1
            else:
                if sh == "Blocked":
                    blocked += 1
                elif sh == "Deleted":
                    deleted += 1
                elif sh == "Error":
                    failed += 1
        except Exception:
            failed += 1
        done += 1
        idx += 1
        await asyncio.sleep(2)
        if done % 20 == 0:
            await sts.edit(
                f"Broadcast in progress:\n\n"
                f"Total Users: {total_users}\n"
                f"Skipped: {skip}\n"
                f"Completed: {done + skip} / {total_users}\n"
                f"Success: {success}\n"
                f"Blocked: {blocked}\n"
                f"Deleted: {deleted}\n"
                f"Failed: {failed}"
            )

    time_taken = datetime.datetime.now() - start_time
    await sts.edit(
        f"Broadcast Completed:\n"
        f"Completed in {time_taken}.\n\n"
        f"Total Users: {total_users}\n"
        f"Skipped: {skip}\n"
        f"Completed: {done + skip} / {total_users}\n"
        f"Success: {success}\n"
        f"Blocked: {blocked}\n"
        f"Deleted: {deleted}\n"
        f"Failed: {failed}"
    )
