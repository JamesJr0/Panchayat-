from pyrogram import Client, filters
import datetime
import time
import asyncio
import logging

from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages


@Client.on_message(filters.command("skipbroadcast") & filters.user(ADMINS))
async def skip_broadcast_cmd(bot, message):
    try:
        skip = int(message.command[1])
        await db.set_skip_count(skip)
        await message.reply_text(f"✅ Next broadcast will skip first <b>{skip}</b> users.")
    except:
        await message.reply_text("❌ Usage: <code>/skipbroadcast 1000</code>")


@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def verupikkals(bot, message):
    users = await db.get_all_users()
    skip = await db.get_skip_count()
    b_msg = message.reply_to_message

    sts = await message.reply_text("Broadcasting your message...")
    start_time = time.time()

    total_users = await db.total_users_count()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    idx = 0

    async for user in users:
        idx += 1
        if idx <= skip:
            continue  # skip this user

        pti, sh = await broadcast_messages(int(user['id']), b_msg)
        if pti:
            success += 1
        elif pti == False:
            if sh == "Blocked":
                blocked += 1
            elif sh == "Deleted":
                deleted += 1
            elif sh == "Error":
                failed += 1

        done += 1
        await asyncio.sleep(2)

        if done % 20 == 0:
            await sts.edit(
                f"Broadcast in progress:\n\n"
                f"Total Users: {total_users}\n"
                f"Completed: {done} / {total_users}\n"
                f"✅ Success: {success}\n"
                f"⛔ Blocked: {blocked}\n"
                f"🗑️ Deleted: {deleted}\n"
                f"⚠️ Failed: {failed}"
            )

    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(
        f"✅ Broadcast Completed in {time_taken}.\n\n"
        f"Total Users: {total_users}\n"
        f"Completed: {done} / {total_users}\n"
        f"✅ Success: {success}\n"
        f"⛔ Blocked: {blocked}\n"
        f"🗑️ Deleted: {deleted}\n"
        f"⚠️ Failed: {failed}"
    )

    await db.set_skip_count(0)
