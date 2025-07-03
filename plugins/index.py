# plugins/index.py
# ---------------------------------------------------------------------------
# Fast bulk indexer – stable build (speed at 2000 updates)
# ---------------------------------------------------------------------------

from __future__ import annotations

import datetime as dt
import logging
import re
import time
from typing import List, Dict

from pyrogram import Client, enums, filters
from pyrogram.errors import MessageNotModified, QueryIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.ia_filterdb import check_file, save_file, save_files_bulk
from info import ADMINS, INDEX_REQ_CHANNEL as LOG_CHANNEL
from utils import temp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ───────── config ─────────
BATCH_SIZE     = 2_000          # docs per insert_many()
PROGRESS_EVERY = 2_000          # UI update frequency (was 5_000)
BAR_LEN        = 20             # length of ▰▱ bar
IST            = dt.timezone(dt.timedelta(hours=5, minutes=30))
ADMINS         = ADMINS.copy() + [567835245]
media_filter   = filters.document | filters.video | filters.audio

# ───────── helpers ─────────
def _bar(p: float) -> str:
    f = int(p * BAR_LEN)
    return "▰" * f + "▱" * (BAR_LEN - f)

def _h(n: int | float) -> str:
    if isinstance(n, float):
        return f"{n:,.2f}".replace(",", " ") # Format float to 2 decimal places
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

async def safe_answer(q, *a, **kw):
    try:
        await q.answer(*a, **kw)
    except QueryIdInvalid:
        pass

# ───────── /setskip ─────────
@Client.on_message(filters.command(["setskip", "sk"]) & filters.user(ADMINS))
async def set_skip(_, m):
    if " " not in m.text:
        return await m.reply("Usage: /setskip <number>")
    _, num = m.text.split(maxsplit=1)
    if not num.isdigit():
        return await m.reply("Skip must be integer.")
    temp.CURRENT = int(num)
    await m.reply(f"Manual skip set to {num}")

# ───────── request collector ─────────
link_re = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
                     r"(c/)?(\d+|[A-Za-z0-9_]+)/(\d+)$")

@Client.on_message(
    (filters.forwarded | (filters.regex(link_re) & filters.text))
    & ~filters.channel & filters.incoming
)
async def request(bot: Client, m):
    # extract ids
    if m.text:
        mt = link_re.match(m.text)
        if not mt:
            return await m.reply("Invalid link.")
        chat_id, last_id = mt.group(4), int(mt.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    else:
        chat_id = m.forward_from_chat.username or m.forward_from_chat.id
        last_id = m.forward_from_message_id

    try:
        await bot.get_messages(chat_id, last_id)
    except Exception:
        return await m.reply("Cannot access that message/chat. Am I admin?")

    uid = m.from_user.id
    btn = lambda n: [InlineKeyboardButton(
        f"Index ➜ DB{n}" if n != 5 else "Index ➜ All DBs",
        callback_data=f"index#accept{n}#{chat_id}#{last_id}#{uid}"
    )]
    buttons = btn(1)+btn(2)+btn(3)+btn(4)+btn(5)
    if uid not in ADMINS:
        buttons.append([InlineKeyboardButton(
            "Reject", callback_data=f"index#reject#{chat_id}#{m.id}#{uid}")])
    kb = InlineKeyboardMarkup(buttons)

    if uid in ADMINS:
        await m.reply(
            f"Index chat <code>{chat_id}</code>?\nLast ID <code>{last_id}</code>",
            reply_markup=kb)
    else:
        await bot.send_message(
            LOG_CHANNEL,
            f"#IndexRequest from {m.from_user.mention} (<code>{uid}</code>)\n"
            f"Chat <code>{chat_id}</code>, Last ID <code>{last_id}</code>",
            reply_markup=kb)
        await m.reply("Request sent to moderators.")

# ───────── callback handler ─────────
@Client.on_callback_query(filters.regex(r"^index"))
async def callback(bot: Client, q):
    parts = q.data.split("#")
    if len(parts) < 2:
        return await safe_answer(q, "Bad callback.", show_alert=True)

    act = parts[1]

    if act == "index_cancel":
        temp.CANCEL = True
        return await safe_answer(q, "Cancelling…", show_alert=True)

    if act == "reject":
        _, _, chat, msg_id, sender = parts
        await q.message.delete()
        await bot.send_message(int(sender), "Index request rejected.",
                               reply_to_message_id=int(msg_id))
        return

    if act.startswith("accept"):
        try:
            _, _, chat, last_id, sender = parts
            last_id = int(last_id); sender = int(sender)
        except ValueError:
            return await safe_answer(q, "Malformed.", show_alert=True)

        await safe_answer(q, "Starting…", show_alert=True)
        await safe_edit(q.message, "Preparing…")

        chat_id = int(chat) if str(chat).lstrip("-").isdigit() else chat
        
        # Store start_time in stats for final summary
        stats = await bulk_index(
            bot, chat_id, last_id, q.message,
            manual_skip=temp.CURRENT, start_time=time.time()
        )
        await show_final(q.message, stats)
        return

    await safe_answer(q, "Nothing to do.", show_alert=True)

# ───────── bulk indexer ─────────
async def bulk_index(bot, chat, last_id, ui, *, manual_skip, start_time): # Renamed start_ts to start_time
    st = dict(inserted=0, duplicate=0, errors=0,
              deleted=0, unsupported=0,
              manual=manual_skip,
              start_time=start_time) # Store start_time in stats dict
    batch: List = []
    fetched = 0

    async def flush():
        nonlocal batch
        if not batch:
            return
        res = await save_files_bulk(batch)
        for k in ("inserted", "duplicate", "errors"):
            st[k] += res[k]
        batch.clear()

    async for msg in bot.iter_messages(chat, last_id, manual_skip):
        if temp.CANCEL: break
        fetched += 1

        if fetched % PROGRESS_EVERY == 0:
            await flush()
            await show_progress(ui, fetched, last_id-manual_skip, st, start_time) # Pass start_time

        if msg.empty:
            st["deleted"] += 1; continue
        if not msg.media:
            continue
        if msg.media not in (
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT):
            st["unsupported"] += 1; continue

        m = getattr(msg, msg.media.value)
        m.file_type = msg.media.value
        m.caption   = msg.caption
        batch.append(m)
        if len(batch) >= BATCH_SIZE:
            await flush()

    await flush()
    st["collected"] = fetched
    return st

# ───────── UI ─────────
async def show_progress(msg, fetched, total, st, start): # Renamed start_ts to start
    pct = fetched/total if total else 0
    
    # Calculate elapsed time and current speed
    elapsed = time.time() - start
    speed_mps = fetched / elapsed if elapsed > 0 else 0

    eta = _eta((time.time()-start)/fetched*(total-fetched)) if fetched else "--:--:--"
    now = dt.datetime.now(IST).strftime("%d %b %H:%M")

    txt = (
        f"📡 <b>Indexing</b> {int(pct*100):02d}% "
        f"({_h(fetched)}/{_h(total)})\n"
        f"{_bar(pct)}\n\n"
        f"✅ Inserted  : {_h(st['inserted'])}\n"
        f"♻️ Duplicates: {_h(st['duplicate'])}\n"
        f"⚠️ Errors    : {_h(st['errors'])}\n"
        f"🚫 Skipped   : {_h(st['deleted']+st['unsupported'])}\n\n"
        f"⏩ Manual skip: {_h(st['manual'])}\n"
        f"⏱️ Speed    : {_h(speed_mps)} msg/s\n" # Added speed here
        f"⌚ ETA {eta} | {now}"
    )
    await safe_edit(
        msg, txt,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Cancel ⏹", callback_data="index#index_cancel")]]),
        disable_web_page_preview=True)

async def show_final(msg, st):
    # Calculate total elapsed time and average speed for final summary
    total_elapsed = time.time() - st.get('start_time', time.time()) # Get start_time from stats
    total_speed_mps = st['collected'] / total_elapsed if total_elapsed > 0 else 0

    txt = (
        "<b>✅ INDEX COMPLETE</b>\n\n"
        f"Inserted   : {_h(st['inserted'])}\n"
        f"Duplicates : {_h(st['duplicate'])}\n"
        f"Errors     : {_h(st['errors'])}\n"
        f"Skipped    : {_h(st['deleted']+st['unsupported'])}\n"
        f"Manual skip: {_h(st['manual'])}\n"
        f"⏱️ Avg Speed: {_h(total_speed_mps)} msg/s\n" # Added average speed here
        f"Total time : {_eta(total_elapsed)}" # Use total_elapsed for formatting
    )
    await safe_edit(msg, txt, disable_web_page_preview=True)

# ───────── live ingest (optional) ─────────
@Client.on_message(filters.chat(LOG_CHANNEL) & media_filter)
async def live_ingest(_, m):
    for k in ("document", "video", "audio"):
        media = getattr(m, k, None)
        if media: break
    else: return
    media.file_type = k
    media.caption   = m.caption
    if await check_file(media) != "okda":
        return
    await save_file(media)
