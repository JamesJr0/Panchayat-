# plugins/index.py
# ---------------------------------------------------------------------------
# Fast bulk indexer for Panchayath bot
# ---------------------------------------------------------------------------

from __future__ import annotations

import datetime as dt
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

# ─────────── configuration ────────────────────────────────────────────────
BATCH_SIZE     = 2_000   # docs per insert_many
PROGRESS_EVERY = 5_000   # UI update frequency
BAR_LEN        = 20      # ▰▱ bar length

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
media_filter = filters.document | filters.video | filters.audio
ADMINS = ADMINS.copy() + [567835245]  # extra admin id

# ─────────── helpers ──────────────────────────────────────────────────────
def _bar(p: float) -> str:
    filled = int(p * BAR_LEN)
    return "▰" * filled + "▱" * (BAR_LEN - filled)

def _h(n: int) -> str:
    return f"{n:,}".replace(",", " ")

def _eta(seconds: float) -> str:
    if seconds <= 0 or seconds == float("inf"):
        return "--:--:--"
    h, m = divmod(int(seconds), 3600)
    m, s = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"

async def safe_edit(msg, *args, **kwargs):
    try:
        await msg.edit(*args, **kwargs)
    except MessageNotModified:
        pass

# ─────────── /setskip ─────────────────────────────────────────────────────
@Client.on_message(filters.command(["setskip", "sk"]) & filters.user(ADMINS))
async def set_skip(_, m):
    if " " not in m.text:
        return await m.reply("Usage: /setskip <number>")
    _, num = m.text.split(maxsplit=1)
    if not num.isdigit():
        return await m.reply("Skip must be integer.")
    temp.CURRENT = int(num)
    await m.reply(f"Manual skip set to {num}")

# ─────────── request collector (DM + group) ───────────────────────────────
link_re = re.compile(
    r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
    r"(c/)?(\d+|[A-Za-z0-9_]+)/(\d+)$"
)

@Client.on_message(
    (filters.forwarded | (filters.regex(link_re) & filters.text))
    & ~filters.channel & filters.incoming
)
async def request(bot: Client, m):
    # 1) extract chat_id & last_msg_id
    if m.text:
        match = link_re.match(m.text)
        if not match:
            return await m.reply("Invalid link.")
        chat_id, last_id = match.group(4), int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif (
        m.forward_from_chat
        and m.forward_from_chat.type == enums.ChatType.CHANNEL
    ):
        chat_id = m.forward_from_chat.username or m.forward_from_chat.id
        last_id = m.forward_from_message_id
    else:
        return

    # 2) quick access test
    try:
        await bot.get_messages(chat_id, last_id)
    except Exception:
        return await m.reply("Cannot access that message/chat. Am I admin?")

    uid = m.from_user.id
    buttons = [
        [InlineKeyboardButton("Index ➜ DB1",
                              callback_data=f"index#accept1#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index ➜ DB2",
                              callback_data=f"index#accept2#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index ➜ DB3",
                              callback_data=f"index#accept3#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index ➜ DB4",
                              callback_data=f"index#accept4#{chat_id}#{last_id}#{uid}")],
        [InlineKeyboardButton("Index ➜ All DBs",
                              callback_data=f"index#accept5#{chat_id}#{last_id}#{uid}")]
    ]
    if uid not in ADMINS:
        buttons.append([InlineKeyboardButton("Reject",
                          callback_data=f"index#reject#{chat_id}#{m.id}#{uid}")])
    kb = InlineKeyboardMarkup(buttons)

    if uid in ADMINS:
        await m.reply(
            f"Index this chat?\nChat: <code>{chat_id}</code>\n"
            f"Last Msg ID: <code>{last_id}</code>",
            reply_markup=kb)
    else:
        await bot.send_message(
            LOG_CHANNEL,
            f"#IndexRequest\nFrom {m.from_user.mention} (<code>{uid}</code>)\n"
            f"Chat <code>{chat_id}</code>, Last ID <code>{last_id}</code>",
            reply_markup=kb)
        await m.reply("Request sent to moderators.")

# ─────────── callback handler ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^index"))
async def callback(bot: Client, q):
    parts = q.data.split("#")          # e.g. ['index', 'accept1', ...]
    if len(parts) < 2:
        return await q.answer("Bad callback.", show_alert=True)

    action = parts[1]

    # cancel
    if action == "index_cancel":
        temp.CANCEL = True
        return await q.answer("Cancelling…", show_alert=True)

    # reject
    if action == "reject":
        _, _, chat, msg_id, sender = parts
        await q.message.delete()
        await bot.send_message(int(sender), "Index request rejected.",
                               reply_to_message_id=int(msg_id))
        return

    # accept buttons
    if action.startswith("accept"):
        try:
            _, _, chat, last_id, sender = parts
            last_id = int(last_id)
            sender = int(sender)
        except ValueError:
            return await q.answer("Malformed callback.", show_alert=True)

        await q.answer("Starting…", show_alert=True)
        await safe_edit(q.message, "Preparing…")

        chat_id = int(chat) if str(chat).lstrip("-").isdigit() else chat
        stats = await bulk_index(
            bot,
            chat_id,
            last_id,
            q.message,
            manual_skip=temp.CURRENT,
            start_ts=time.time(),
        )
        await show_final(q.message, stats)
        return

    await q.answer("Nothing to do.", show_alert=True)

# ─────────── bulk indexer ─────────────────────────────────────────────────
async def bulk_index(
    bot: Client,
    chat,
    last_msg_id: int,
    ui_msg,
    *,
    manual_skip: int,
    start_ts: float,
) -> Dict[str, int]:
    st = dict(
        inserted=0,
        duplicate=0,
        errors=0,
        deleted=0,
        unsupported=0,
        manual=manual_skip,
    )
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

    async for msg in bot.iter_messages(chat, last_msg_id, manual_skip):
        if temp.CANCEL:
            break

        fetched += 1
        if fetched % PROGRESS_EVERY == 0:
            await flush()
            await show_progress(
                ui_msg, fetched, last_msg_id - manual_skip, st, start_ts
            )

        if msg.empty:
            st["deleted"] += 1
            continue
        if not msg.media:
            continue
        if msg.media not in (
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT,
        ):
            st["unsupported"] += 1
            continue

        media = getattr(msg, msg.media.value, None)
        if not media:
            st["unsupported"] += 1
            continue

        media.file_type = msg.media.value
        media.caption = msg.caption
        batch.append(media)

        if len(batch) >= BATCH_SIZE:
            await flush()

    await flush()
    st["collected"] = fetched
    return st

# ─────────── UI rendering ────────────────────────────────────────────────
async def show_progress(msg, fetched: int, total: int, st: Dict[str, int], start: float):
    pct = fetched / total if total else 0
    eta = _eta((time.time() - start) / fetched * (total - fetched)) if fetched else "--:--:--"
    now = dt.datetime.now(IST).strftime("%d %b %H:%M")

    text = (
        f"📡 <b>Indexing</b> {int(pct*100):02d}%  "
        f"({_h(fetched)}/{_h(total)})\n"
        f"{_bar(pct)}\n\n"
        f"✅ Inserted  : {_h(st['inserted'])}\n"
        f"♻️ Duplicates: {_h(st['duplicate'])}\n"
        f"⚠️ Errors    : {_h(st['errors'])}\n"
        f"🚫 Skipped   : {_h(st['deleted'] + st['unsupported'])}\n\n"
        f"⏩ Manual skip: {_h(st['manual'])}\n"
        f"⌚ ETA {eta} | {now}"
    )
    await safe_edit(
        msg,
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Cancel ⏹", callback_data="index#index_cancel")]]
        ),
        disable_web_page_preview=True,
    )

async def show_final(msg, st: Dict[str, int]):
    text = (
        "<b>✅ INDEX COMPLETE</b>\n\n"
        f"Inserted   : {_h(st['inserted'])}\n"
        f"Duplicates : {_h(st['duplicate'])}\n"
        f"Errors     : {_h(st['errors'])}\n"
        f"Skipped    : {_h(st['deleted'] + st['unsupported'])}\n"
        f"Manual skip: {_h(st['manual'])}"
    )
    await safe_edit(msg, text, disable_web_page_preview=True)

# ─────────── live ingest (optional) ───────────────────────────────────────
@Client.on_message(filters.chat(LOG_CHANNEL) & media_filter)
async def live_ingest(_, m):
    for kind in ("document", "video", "audio"):
        media = getattr(m, kind, None)
        if media:
            break
    else:
        return
    media.file_type = kind
    media.caption = m.caption
    if await check_file(media) != "okda":
        return
    await save_file(media)
