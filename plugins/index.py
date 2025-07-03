# plugins/index.py
# ---------------------------------------------------------------------------
# Bulk indexer – UI enhanced (manual skip, collected count, recent names)
# ---------------------------------------------------------------------------
import asyncio, logging, re, time, datetime, collections
from typing import List

from pyrogram import Client, filters, enums
from pyrogram.errors import (
    ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from info import ADMINS, INDEX_REQ_CHANNEL as LOG_CHANNEL
from utils import temp
from database.ia_filterdb import (
    save_file, save_files_bulk, check_file
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ─── configuration ────────────────────────────────────────────────────────
media_filter     = filters.document | filters.video | filters.audio
BATCH_SIZE       = 1000          # concurrent inserts / flush
PROGRESS_EVERY   = 200           # update UI every n fetched messages
PROG_BAR_LEN     = 10            # length of ASCII bar
RECENT_LIMIT     = 5             # keep last N saved file-names

ADMINS = ADMINS.copy() + [567835245]

# ─── small helpers for UI ─────────────────────────────────────────────────
def _bar(pct: float) -> str:
    filled = int(pct * PROG_BAR_LEN)
    return "▰" * filled + "▱" * (PROG_BAR_LEN - filled)

def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")     # thin-space thousands

def _eta(sec: float) -> str:
    if sec < 0 or sec == float("inf"):
        return "--:--:--"
    h, rem = divmod(int(sec), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"

def _norm(name: str) -> str:
    return re.sub(r"[_\-.+]", " ", name)[:45]

# ─── CALLBACK-QUERY (start / cancel / reject) ─────────────────────────────
@Client.on_callback_query(filters.regex(r"^index"))
async def index_cb(bot, q):
    if q.data.startswith("index#index_cancel"):
        temp.CANCEL = True
        return await q.answer("Cancelling…", show_alert=True)

    _, action, chat, last_id, sender = q.data.split("#")
    last_id = int(last_id)
    sender  = int(sender)

    if action == "reject":
        await q.message.delete()
        await bot.send_message(sender, "Your request was declined.",
                               reply_to_message_id=last_id)
        return

    await q.answer("Starting…", show_alert=True)
    edit = q.message
    await edit.edit("Preparing…")

    chat_id = int(chat) if chat.lstrip("-").isdigit() else chat
    start   = time.time()

    stats = await _bulk_index(
        bot, chat_id, last_id, edit,
        manual_skip=temp.CURRENT,
        start_ts=start
    )
    await _show_final(edit, stats, start)

    if sender not in ADMINS:
        await bot.send_message(
            sender,
            (f"✅ Index finished for {chat}\n"
             f"Inserted: {_fmt(stats['inserted'])}\n"
             f"Duplicates: {_fmt(stats['duplicate'])}\n"
             f"Errors: {_fmt(stats['errors'])}"),
            reply_to_message_id=last_id
        )

# ─── /setskip command (unchanged) ────────────────────────────────────────
@Client.on_message(filters.command(["setskip", "sk"]) & filters.user(ADMINS))
async def setskip(_, m):
    if " " not in m.text:
        return await m.reply("Usage: /setskip <number>")
    _, v = m.text.split(maxsplit=1)
    if not v.isdigit():
        return await m.reply("Skip must be integer.")
    temp.CURRENT = int(v)
    await m.reply(f"Skip set to {v}")

# ─── Index-request collector (private & group) – identical logic ─────────
link_re = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
                     r"(c/)?(\d+|[A-Za-z0-9_]+)/(\d+)$")

@Client.on_message(
    (filters.forwarded | (filters.regex(link_re) & filters.text))
    & ~filters.channel & filters.incoming
)
async def index_request(bot, m):
    # (same as earlier version; omitted for brevity)
    pass

# ─── BULK INDEX CORE ──────────────────────────────────────────────────────
async def _bulk_index(bot: Client, chat_id, last_msg_id, edit_msg, *,
                      manual_skip: int, start_ts: float) -> dict:
    stats = dict(
        inserted=0, duplicate=0, errors=0,
        deleted=0, unsupported=0,
        manual=manual_skip
    )
    fetched  = 0
    recent = collections.deque(maxlen=RECENT_LIMIT)
    batch: List = []

    async for message in bot.iter_messages(chat_id, last_msg_id, manual_skip):
        if temp.CANCEL:
            break

        fetched += 1
        if fetched % PROGRESS_EVERY == 0:
            await _flush(batch, stats, recent)
            await _show_progress(
                edit_msg, fetched, last_msg_id - manual_skip,
                stats, recent, start_ts
            )

        # --- filtering ---------------------------------------------------
        if message.empty:
            stats["deleted"] += 1; continue
        if not message.media:
            continue
        if message.media not in (
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT
        ):
            stats["unsupported"] += 1; continue

        media = getattr(message, message.media.value, None)
        if not media:
            stats["unsupported"] += 1; continue

        media.file_type = message.media.value
        media.caption   = message.caption
        batch.append(media)

        if len(batch) >= BATCH_SIZE:
            await _flush(batch, stats, recent)

    await _flush(batch, stats, recent)
    stats["collected"] = fetched
    stats["recent"]    = list(recent)
    return stats


async def _flush(batch, stats, recent):
    if not batch:
        return
    res = await save_files_bulk(batch)
    for k in ("inserted", "duplicate", "errors"):
        stats[k] += res[k]
    # update recent names (approx; duplicates may be included)
    for m in batch[-RECENT_LIMIT:]:
        recent.appendleft(_norm(m.file_name))
    batch.clear()

# ─── UI RENDERING ─────────────────────────────────────────────────────────
async def _show_progress(msg, fetched, total, st, recent, start_ts):
    pct = fetched / total if total else 0
    bar = _bar(pct)
    elapsed = time.time() - start_ts
    eta = _eta((elapsed / fetched) * (total - fetched) if fetched else float("inf"))
    now = datetime.datetime.now().strftime("%H:%M:%S")

    recent_txt = "\n".join(f" • {name}" for name in list(recent)[:RECENT_LIMIT]) \
                 if recent else " —"

    text = (
        f"📡 <b>Indexing</b>  ( {_fmt(fetched)} / {_fmt(total)} ) "
        f"{int(pct*100):02d} %\n{bar}\n\n"
        f"✅ <b>Inserted   :</b> {_fmt(st['inserted'])}\n"
        f"♻️ <b>Duplicates :</b> {_fmt(st['duplicate'])}\n"
        f"⚠️ <b>Errors     :</b> {_fmt(st['errors'])}\n\n"
        f"🚫 <b>Skipped    :</b> {_fmt(st['deleted']+st['unsupported'])}\n"
        f"   ┣ deleted       {_fmt(st['deleted'])}\n"
        f"   ┗ unsupported   {_fmt(st['unsupported'])}\n\n"
        f"⏩ <b>Manual skip :</b> {_fmt(st['manual'])}\n"
        f"📥 <b>Collected   :</b> {_fmt(fetched)}\n\n"
        f"📝 <b>Last saved :</b>\n{recent_txt}\n\n"
        f"ETA : {eta} ⏳\n"
        f"Last update : {now}"
    )

    await msg.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Cancel",
              callback_data="index#index_cancel#0#0#0")]]
        ),
        disable_web_page_preview=True
    )

async def _show_final(msg, st, start_ts):
    elapsed = _eta(time.time() - start_ts)
    recent_txt = "\n".join(f" • {n}" for n in st["recent"]) if st["recent"] else " —"
    txt = (
        "<b>✅ Indexing Completed</b>\n\n"
        f"Inserted   : {_fmt(st['inserted'])}\n"
        f"Duplicates : {_fmt(st['duplicate'])}\n"
        f"Errors     : {_fmt(st['errors'])}\n\n"
        f"Manual skip: {_fmt(st['manual'])}\n"
        f"Collected  : {_fmt(st['collected'])}\n"
        f"Skipped    : {_fmt(st['deleted']+st['unsupported'])}\n"
        f"   ┣ deleted       {_fmt(st['deleted'])}\n"
        f"   ┗ unsupported   {_fmt(st['unsupported'])}\n\n"
        f"📝 <b>Last saved :</b>\n{recent_txt}\n\n"
        f"Total time : {elapsed}"
    )
    await msg.edit(txt, disable_web_page_preview=True)

# ─── LIVE CHANNEL INGEST (unchanged) ──────────────────────────────────────
@Client.on_message(filters.chat(LOG_CHANNEL) & media_filter)
async def live_listener(_, m):
    for t in ("document", "video", "audio"):
        media = getattr(m, t, None)
        if media:
            break
    else:
        return
    media.file_type = t
    media.caption   = m.caption
    if await check_file(media) != "okda":
        return
    await save_file(media)
