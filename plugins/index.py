# plugins/index.py
# ---------------------------------------------------------------------------
# Fast bulk indexer for Panchayath bot
# UI-minimal, 7-lakh rollover handled inside ia_filterdb
# ---------------------------------------------------------------------------

from __future__ import annotations

import datetime as _dt
import logging
import re
import time
from typing import List, Dict

from pyrogram import Client, enums, filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.ia_filterdb import check_file, save_file, save_files_bulk
from info import ADMINS, INDEX_REQ_CHANNEL as LOG_CHANNEL
from utils import temp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ────────── CONFIG ────────────────────────────────────────────────────────
media_filter   = filters.document | filters.video | filters.audio
BATCH_SIZE     = 2_000          # docs per insert_many()
PROGRESS_EVERY = 5_000          # UI refresh frequency
BAR_LEN        = 20             # length of ▰▱ bar

IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30))

ADMINS = ADMINS.copy() + [567835245]   # extra hard-coded admin id

# ────────── HELPERS ───────────────────────────────────────────────────────
def _bar(p: float) -> str:
    done = int(p * BAR_LEN)
    return "▰" * done + "▱" * (BAR_LEN - done)

def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")

def _eta(sec: float) -> str:
    if sec <= 0 or sec == float("inf"):
        return "--:--:--"
    h, m = divmod(int(sec), 3600)
    m, s = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"

async def safe_edit(msg, *a, **kw):
    try:
        await msg.edit(*a, **kw)
    except MessageNotModified:
        pass

# ────────── /setskip ──────────────────────────────────────────────────────
@Client.on_message(filters.command(["setskip", "sk"]) & filters.user(ADMINS))
async def set_skip(_, m):
    if " " not in m.text:
        return await m.reply("Usage: /setskip <number>")
    _, num = m.text.split(maxsplit=1)
    if not num.isdigit():
        return await m.reply("Skip must be integer.")
    temp.CURRENT = int(num)
    await m.reply(f"Manual skip set to {num}")

# ────────── REQUEST COLLECTOR (PM & GROUP) ────────────────────────────────
link_re = re.compile(
    r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
    r"(c/)?(\d+|[A-Za-z0-9_]+)/(\d+)$"
)

@Client.on_message(
    (filters.forwarded | (filters.regex(link_re) & filters.text))
    & ~filters.channel & filters.incoming
)
async def request(bot: Client, m):
    # extract IDs
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

    try:
        await bot.get_messages(chat_id, last_id)
    except Exception:
        return await m.reply("Cannot access that message/chat. Am I admin?")

    uid = m.from_user.id
    buttons = [
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
        buttons.append([InlineKeyboardButton("Reject",
                     callback_data=f"index#reject#{chat_id}#{m.id}#{uid}")])
    kb = InlineKeyboardMarkup(buttons)

    if uid in ADMINS:
        await m.reply(
            f"Index this chat?\nChat: <code>{chat_id}</code>\n"
            f"Last ID: <code>{last_id}</code>", reply_markup=kb)
    else:
        await bot.send_message(
            LOG_CHANNEL,
            f"#IndexRequest\nFrom {m.from_user.mention} (<code>{uid}</code>)\n"
            f"Chat <code>{chat_id}</code>, Last ID <code>{last_id}</code>",
            reply_markup=kb)
        await m.reply("Request sent for approval.")

# ────────── CALLBACK (start / cancel / reject) ────────────────────────────
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
    await safe_edit(q.message, "Preparing…")

    chat_id = int(chat) if str(chat).lstrip("-").isdigit() else chat
    stats = await bulk_index(
        bot, chat_id, last, q.message,
        manual_skip=temp.CURRENT,
        start_ts=time.time()
    )
    await show_final(q.message, stats)

# ────────── BULK INDEXER ──────────────────────────────────────────────────
async def bulk_index(bot: Client, chat, last_id, ui_msg, *,
                     manual_skip: int, start_ts: float) -> Dict[str, int]:
    st = dict(inserted=0, duplicate=0, errors=0,
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
            st[k] += res[k]
        batch.clear()

    async for m in bot.iter_messages(chat, last_id, manual_skip):
        if temp.CANCEL:
            break
        fetched += 1

        if fetched % PROGRESS_EVERY == 0:
            await flush()
            await show_progress(ui_msg, fetched, last_id - manual_skip, st, start_ts)

        if m.empty:
            st["deleted"] += 1; continue
        if not m.media:
            continue
        if m.media not in (
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT):
            st["unsupported"] += 1; continue

        md = getattr(m, m.media.value)
        md.file_type = m.media.value
        md.caption   = m.caption
        batch.append(md)
        if len(batch) >= BATCH_SIZE:
            await flush()

    await flush()
    st["collected"] = fetched
    return st

# ────────── UI RENDERING ──────────────────────────────────────────────────
async def show_progress(msg, fetched, total, st, start):
    pct = fetched / total if total else 0
    bar = _bar(pct)
    eta = _eta((time.time()-start)/fetched*(total-fetched)) if fetched else "--:--:--"
    now = _dt.datetime.now(IST).strftime("%d %b %H:%M")

    text = (
        f"📡 <b>Indexing</b> {int(pct*100):02d}%  "
        f"({_fmt(fetched)}/{_fmt(total)})\n"
        f"{bar}\n\n"
        f"✅ Inserted : {_fmt(st['inserted'])}\n"
        f"♻️ Dupes    : {_fmt(st['duplicate'])}\n"
        f"⚠️ Errors   : {_fmt(st['errors'])}\n"
        f"🚫 Skipped  : {_fmt(st['deleted']+st['unsupported'])}\n\n"
        f"⏩ Manual skip : {_fmt(st['manual'])}\n"
        f"⌚ ETA {eta} | {now}"
    )
    await safe_edit(
        msg, text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Cancel ⏹", callback_data="index#index_cancel")]]),
        disable_web_page_preview=True
    )

async def show_final(msg, st):
    txt = (
        "<b>✅ INDEX COMPLETE</b>\n\n"
        f"Inserted   : {_fmt(st['inserted'])}\n"
        f"Duplicates : {_fmt(st['duplicate'])}\n"
        f"Errors     : {_fmt(st['errors'])}\n"
        f"Skipped    : {_fmt(st['deleted']+st['unsupported'])}\n"
        f"Manual skip: {_fmt(st['manual'])}"
    )
    await safe_edit(msg, txt, disable_web_page_preview=True)

# ────────── LIVE CHANNEL INGEST (optional) ────────────────────────────────
@Client.on_message(filters.chat(LOG_CHANNEL) & media_filter)
async def live_ingest(_, m):
    for kind in ("document", "video", "audio"):
        media = getattr(m, kind, None)
        if media:
            break
    else:
        return
    media.file_type = kind
    media.caption   = m.caption
    if await check_file(media) != "okda":
        return
    await save_file(media)
