# plugins/index.py
# ---------------------------------------------------------------------------
# Bulk indexer – 2025-07-03
# ---------------------------------------------------------------------------
from __future__ import annotations

import asyncio
import collections
import datetime as _dt
import logging
import re
import time
from typing import List

from pyrogram import Client, enums, filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.ia_filterdb import (
    check_file,
    save_file,
    save_files_bulk,
)
from info import ADMINS, INDEX_REQ_CHANNEL as LOG_CHANNEL
from utils import temp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ───────────────────────── config ─────────────────────────
media_filter = filters.document | filters.video | filters.audio
BATCH_SIZE     = 3000  # Changed from 1000 to 3000
PROGRESS_EVERY = 200
BAR_LEN        = 10

IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30))

ADMINS = ADMINS.copy() + [567835245]

# ───────────────────────── helpers ─────────────────────────
def _bar(p: float) -> str:
    filled = int(p * BAR_LEN)
    return "▰" * filled + "▱" * (BAR_LEN - filled)

def _h(n: int) -> str:                         # format number
    return f"{n:,}".replace(",", " ")

def _eta(sec: float) -> str:
    if sec <= 0 or sec == float("inf"):
        return "--:--:--"
    h, rem = divmod(int(sec), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"

async def _safe_edit(msg, *a, **kw):
    try:
        await msg.edit(*a, **kw)
    except MessageNotModified:
        pass

# ───────────────────────── /setskip ───────────────────────
@Client.on_message(filters.command(["setskip", "sk"]) & filters.user(ADMINS))
async def setskip(_, m):
    if " " not in m.text:
        return await m.reply("Usage: /setskip <number>")
    _, v = m.text.split(maxsplit=1)
    if not v.isdigit():
        return await m.reply("Skip must be integer.")
    temp.CURRENT = int(v)
    await m.reply(f"Skip set to {v}")

# ───────────────────────── request collector ──────────────
link_re = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
                     r"(c/)?(\d+|[A-Za-z0-9_]+)/(\d+)$")

@Client.on_message(
    (filters.forwarded | (filters.regex(link_re) & filters.text))
    & ~filters.channel & filters.incoming
)
async def index_request(bot: Client, m):
    # 1) extract ids
    if m.text:
        mt = link_re.match(m.text)
        if not mt:
            return await m.reply("Invalid link.")
        chat_id, last_id = mt.group(4), int(mt.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif m.forward_from_chat and m.forward_from_chat.type == enums.ChatType.CHANNEL:
        chat_id = m.forward_from_chat.username or m.forward_from_chat.id
        last_id = m.forward_from_message_id
    else:
        return

    # quick existence check
    try:
        await bot.get_messages(chat_id, last_id)
    except Exception:
        return await m.reply("Cannot access that message/chat. Am I admin?")

    uid = m.from_user.id
    btns = [
        [InlineKeyboardButton("Index To DB1",
                              callback_data=f"index#accept1#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index To DB2",
                              callback_data=f"index#accept2#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index To DB3",
                              callback_data=f"index#accept3#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index To DB4",
                              callback_data=f"index#accept4#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index To All DB",
                              callback_data=f"index#accept5#{chat_id}#{last_id}#{uid}")]
    ]
    if uid not in ADMINS:
        btns.append([InlineKeyboardButton("Reject Index",
                   callback_data=f"index#reject#{chat_id}#{m.id}#{uid}")])

    markup = InlineKeyboardMarkup(btns)

    if uid in ADMINS:
        await m.reply(
            f"Index this chat?\nChat: <code>{chat_id}</code>\nLast ID: <code>{last_id}</code>",
            reply_markup=markup)
    else:
        await bot.send_message(LOG_CHANNEL,
            f"#IndexRequest\nFrom {m.from_user.mention} (<code>{uid}</code>)\n"
            f"Chat <code>{chat_id}</code>, Last ID <code>{last_id}</code>",
            reply_markup=markup)
        await m.reply("Request sent to moderators.")

# ───────────────────────── callback (start/cancel) ────────
@Client.on_callback_query(filters.regex(r"^index"))
async def callback(bot: Client, q):
    _, act, chat, last, sender = q.data.split("#")
    last, sender = int(last), int(sender)

    if act == "index_cancel":
        temp.CANCEL = True
        return await q.answer("Cancelling…", show_alert=True)
    if act == "reject":
        await q.message.delete()
        await bot.send_message(sender, "Index request rejected.",
                               reply_to_message_id=last)
        return

    await q.answer("Starting…", show_alert=True)
    await _safe_edit(q.message, "Preparing…")
    chat_id = int(chat) if str(chat).lstrip("-").isdigit() else chat

    # Set start_time here for overall indexing duration calculation
    temp.START_TIME = time.time() 

    stats = await _bulk_index(
        bot, chat_id, last, q.message,
        manual_skip=temp.CURRENT,
        start_ts=temp.START_TIME # Pass this to _bulk_index
    )
    await _show_final(q.message, stats)

# ───────────────────────── bulk index core ─────────────────
async def _bulk_index(bot: Client, chat, last_id, msg, *,
                      manual_skip: int, start_ts: float):

    stats = dict(inserted=0, duplicate=0, errors=0,
                 deleted=0, unsupported=0,
                 manual=manual_skip)
    fetched = 0
    batch: List = []

    async def flush():
        nonlocal batch
        if not batch:
            return
        res = await save_files_bulk(batch)
        for k in ("inserted", "duplicate", "errors"):
            stats[k] += res[k]
        batch.clear()

    async for m in bot.iter_messages(chat, last_id, manual_skip):
        if temp.CANCEL:
            break
        fetched += 1
        if fetched % PROGRESS_EVERY == 0:
            await flush()
            # Pass the current time to calculate speed
            await _show_progress(msg, fetched, last_id - manual_skip,
                                 stats, start_ts, time.time())

        if m.empty: stats["deleted"] += 1; continue
        if not m.media: continue
        if m.media not in (
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT):
            stats["unsupported"] += 1; continue

        md = getattr(m, m.media.value)
        md.file_type = m.media.value
        md.caption   = m.caption
        batch.append(md)
        if len(batch) >= BATCH_SIZE: # This condition now checks for 3000
            await flush()

    await flush()
    stats["collected"] = fetched
    return stats

# ───────────────────────── UI ──────────────────────────────
async def _show_progress(msg, fetched, total, st, start_ts, current_ts): # Added current_ts
    pct  = fetched/total if total else 0
    bar  = _bar(pct)
    now  = _dt.datetime.now(IST).strftime("%H:%M:%S")

    elapsed_time = current_ts - start_ts
    eta  = _eta(elapsed_time/fetched*(total-fetched)) if fetched and elapsed_time > 0 else "--:--:--"

    # Calculate speed
    speed = (fetched / elapsed_time) if elapsed_time > 0 else 0
    speed_str = f"{speed:.2f} msg/s"

    txt = (
        f"📡 <b>Indexing</b> ( {_h(fetched)} / {_h(total)} ) {int(pct*100):02d}%\n"
        f"{bar}\n\n"
        f"✅ Inserted   : {_h(st['inserted'])}\n"
        f"♻️ Duplicates : {_h(st['duplicate'])}\n"
        f"⚠️ Errors     : {_h(st['errors'])}\n\n"
        f"🚫 Skipped    : {_h(st['deleted']+st['unsupported'])}\n"
        f"   ┣ deleted      {_h(st['deleted'])}\n"
        f"   ┗ unsupported  {_h(st['unsupported'])}\n\n"
        f"⏩ Manual skip : {_h(st['manual'])}\n"
        f"📥 Collected   : {_h(fetched)}\n"
        f"⚡ Speed      : {speed_str}\n\n"
        f"ETA : {eta}   |   Last update : {now}"
    )
    await _safe_edit(msg, txt,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Cancel", callback_data="index#index_cancel")]]),
        disable_web_page_preview=True)

async def _show_final(msg, st):
    elapsed = _eta(time.time() - temp.START_TIME) # Using temp.START_TIME for accuracy
    txt = (
        "<b>✅ Indexing Completed</b>\n\n"
        f"Inserted   : {_h(st['inserted'])}\n"
        f"Duplicates : {_h(st['duplicate'])}\n"
        f"Errors     : {_h(st['errors'])}\n\n"
        f"Manual skip: {_h(st['manual'])}\n"
        f"Collected  : {_h(st['collected'])}\n"
        f"Skipped    : {_h(st['deleted']+st['unsupported'])}\n"
        f"   ┣ deleted      {_h(st['deleted'])}\n"
        f"   ┗ unsupported  {_h(st['unsupported'])}\n\n"
        f"Total time : {elapsed}"
    )
    await _safe_edit(msg, txt, disable_web_page_preview=True)

# ───────────────────────── live listener (optional) ───────
@Client.on_message(filters.chat(LOG_CHANNEL) & media_filter)
async def live_ingest(_, m):
    for ft in ("document", "video", "audio"):
        media = getattr(m, ft, None)
        if media:
            break
    else:
        return
    media.file_type = ft
    media.caption   = m.caption
    if await check_file(media) != "okda":
        return
    await save_file(media)
