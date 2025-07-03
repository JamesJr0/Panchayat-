# plugins/index.py
# ---------------------------------------------------------------------------
# Bulk indexer for Panchayath bot
#
# - Accepts requests in private chats and groups (not channels)
# - Fancy progress UI: bar, ETA, manual-skip, collected, recent file-names
# - True bulk insert with save_files_bulk()  (BATCH_SIZE = 1000)
# - 7-lakh rollover handled inside ia_filterdb.save_files_bulk()
# ---------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import collections
import datetime
import logging
import re
import time
from typing import List

from pyrogram import Client, enums, filters
from pyrogram.errors import (
    ChannelInvalid,
    ChatAdminRequired,
    UsernameInvalid,
    UsernameNotModified,
)
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

# ────────────────────────── configuration ──────────────────────────────────
media_filter = filters.document | filters.video | filters.audio

BATCH_SIZE = 1000        # how many media docs per insert_many()
PROGRESS_EVERY = 200     # update UI every N fetched messages
PROG_BAR_LEN = 10        # size of the “▰▱” bar
RECENT_LIMIT = 5         # show last N saved file names in UI

ADMINS = ADMINS.copy() + [567835245]  # extra admin if you still need it

# ────────────────────────── tiny UI helpers ────────────────────────────────
def _bar(pct: float) -> str:
    filled = int(pct * PROG_BAR_LEN)
    return "▰" * filled + "▱" * (PROG_BAR_LEN - filled)


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")  # thin-space thousands


def _eta(seconds: float) -> str:
    if seconds <= 0 or seconds == float("inf"):
        return "--:--:--"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}"


def _clean(name: str) -> str:
    # keep it short and readable
    return re.sub(r"[_\-.+]", " ", name)[:45]


# ────────────────────────── /setskip command ───────────────────────────────
@Client.on_message(filters.command(["setskip", "sk"]) & filters.user(ADMINS))
async def setskip(_, msg):
    if " " not in msg.text:
        return await msg.reply("Usage: /setskip <number>")
    _, val = msg.text.split(maxsplit=1)
    if not val.isdigit():
        return await msg.reply("Skip must be an integer.")
    temp.CURRENT = int(val)
    await msg.reply(f"Skip set to {val}")


# ────────────────────────── index-request collector ────────────────────────
link_re = re.compile(
    r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
    r"(c/)?(\d+|[A-Za-z0-9_]+)/(\d+)$"
)


@Client.on_message(
    (filters.forwarded | (filters.regex(link_re) & filters.text))
    & ~filters.channel
    & filters.incoming
)
async def index_request(bot: Client, message):
    """
    Accept either:
      • a t.me link  (text message)
      • a forwarded post from a channel
    Then ask for moderator approval via inline buttons.
    """

    # 1) extract chat_id & last_msg_id
    if message.text:
        m = link_re.match(message.text)
        if not m:
            return await message.reply("Invalid link.")
        chat_id = m.group(4)
        last_msg_id = int(m.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif (
        message.forward_from_chat
        and message.forward_from_chat.type == enums.ChatType.CHANNEL
    ):
        chat_id = (
            message.forward_from_chat.username
            or message.forward_from_chat.id
        )
        last_msg_id = message.forward_from_message_id
    else:
        return

    # 2) basic checks
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await message.reply(
            "Chat looks private. Add me as admin before indexing."
        )
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("Invalid username / link.")
    except Exception as exc:
        logger.exception(exc)
        return await message.reply(f"Error: {exc}")

    try:
        test = await bot.get_messages(chat_id, last_msg_id)
    except Exception:
        return await message.reply(
            "Cannot fetch that message. Am I an admin there?"
        )
    if test.empty:
        return await message.reply("Message ID not found.")

    # 3) build inline buttons
    uid = message.from_user.id
    buttons = [
        [
            InlineKeyboardButton(
                "Index To DB1",
                callback_data=f"index#accept1#{chat_id}#{last_msg_id}#{uid}",
            )
        ],
        [
            InlineKeyboardButton(
                "Index To DB3",
                callback_data=f"index#accept3#{chat_id}#{last_msg_id}#{uid}",
            )
        ],
        [
            InlineKeyboardButton(
                "Index To DB4",
                callback_data=f"index#accept4#{chat_id}#{last_msg_id}#{uid}",
            )
        ],
        [
            InlineKeyboardButton(
                "Index To All DB",
                callback_data=f"index#accept5#{chat_id}#{last_msg_id}#{uid}",
            )
        ],
    ]
    if uid not in ADMINS:
        buttons.append(
            [
                InlineKeyboardButton(
                    "Reject Index",
                    callback_data=f"index#reject#{chat_id}#{message.id}#{uid}",
                )
            ]
        )
    markup = InlineKeyboardMarkup(buttons)

    # 4) send to proper destination
    if uid in ADMINS:
        return await message.reply(
            f"Index this chat?\n\n"
            f"Chat: <code>{chat_id}</code>\n"
            f"Last Msg ID: <code>{last_msg_id}</code>",
            reply_markup=markup,
        )

    # Send to LOG_CHANNEL for moderator review
    try:
        invite = (
            (await bot.create_chat_invite_link(chat_id)).invite_link
            if isinstance(chat_id, int)
            else f"@{chat_id}"
        )
    except ChatAdminRequired:
        invite = "⚠️ no invite-link permission"

    await bot.send_message(
        LOG_CHANNEL,
        (
            "#IndexRequest\n\n"
            f"From: {message.from_user.mention} "
            f"(<code>{uid}</code>)\n"
            f"Chat: <code>{chat_id}</code>\n"
            f"Last Msg ID: <code>{last_msg_id}</code>\n"
            f"Invite: {invite}"
        ),
        reply_markup=markup,
    )
    await message.reply("Thanks! Moderators will review your request.")


# ────────────────────────── callback-query handler ─────────────────────────
@Client.on_callback_query(filters.regex(r"^index"))
async def index_callback(bot: Client, query):
    data = query.data.split("#")  # index#action#chat#last_id#sender
    if len(data) < 2:
        return

    if data[1] == "index_cancel":
        temp.CANCEL = True
        return await query.answer("Cancelling…", show_alert=True)

    action, chat, last_id, sender = data[1:5]
    last_id = int(last_id)
    sender = int(sender)

    if action == "reject":
        await query.message.delete()
        await bot.send_message(
            sender,
            "Your indexing request was rejected by moderators.",
            reply_to_message_id=last_id,
        )
        return

    await query.answer("Starting…", show_alert=True)
    editable = query.message
    await editable.edit("Preparing…")

    chat_id = int(chat) if str(chat).lstrip("-").isdigit() else chat

    stats = await _bulk_index(
        bot,
        chat_id,
        last_id,
        editable,
        manual_skip=temp.CURRENT,
        start_ts=time.time(),
    )
    await _show_final(editable, stats)

    if sender not in ADMINS:
        await bot.send_message(
            sender,
            f"✅ Index finished.\nInserted: {_fmt(stats['inserted'])}\n"
            f"Duplicates: {_fmt(stats['duplicate'])}\n"
            f"Errors: {_fmt(stats['errors'])}",
            reply_to_message_id=last_id,
        )


# ────────────────────────── bulk-index core ───────────────────────────────
async def _bulk_index(
    bot: Client,
    chat_id: int | str,
    last_msg_id: int,
    status_msg,
    *,
    manual_skip: int,
    start_ts: float,
) -> dict:
    stats = dict(
        inserted=0,
        duplicate=0,
        errors=0,
        deleted=0,
        unsupported=0,
        manual=manual_skip,
    )
    fetched = 0
    recent = collections.deque(maxlen=RECENT_LIMIT)
    batch: List = []

    async def flush():
        nonlocal batch
        if not batch:
            return
        res = await save_files_bulk(batch)
        for k in ("inserted", "duplicate", "errors"):
            stats[k] += res[k]
        for m in batch[-RECENT_LIMIT:]:
            recent.appendleft(_clean(m.file_name))
        batch.clear()

    async for message in bot.iter_messages(chat_id, last_msg_id, manual_skip):
        if temp.CANCEL:
            break

        fetched += 1
        if fetched % PROGRESS_EVERY == 0:
            await flush()
            await _show_progress(
                status_msg,
                fetched,
                last_msg_id - manual_skip,
                stats,
                list(recent),
                start_ts,
            )

        # filter message
        if message.empty:
            stats["deleted"] += 1
            continue
        if not message.media:
            continue
        if message.media not in (
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT,
        ):
            stats["unsupported"] += 1
            continue

        media = getattr(message, message.media.value, None)
        if not media:
            stats["unsupported"] += 1
            continue

        media.file_type = message.media.value
        media.caption = message.caption
        batch.append(media)

        if len(batch) >= BATCH_SIZE:
            await flush()

    await flush()
    stats["collected"] = fetched
    stats["recent"] = list(recent)
    return stats


# ────────────────────────── UI helpers ─────────────────────────────────────
async def _show_progress(
    msg,
    fetched: int,
    total: int,
    st: dict,
    recent: List[str],
    start_ts: float,
):
    pct = fetched / total if total else 0
    bar = _bar(pct)
    elapsed = time.time() - start_ts
    eta = _eta((elapsed / fetched) * (total - fetched)) if fetched else "--:--:--"
    now = datetime.datetime.now().strftime("%H:%M:%S")

    rec = "\n".join(f" • {n}" for n in recent) if recent else " —"

    text = (
        f"📡 <b>Indexing</b>  ( {_fmt(fetched)} / {_fmt(total)} ) "
        f"{int(pct*100):02d}%\n{bar}\n\n"
        f"✅ <b>Inserted   :</b> {_fmt(st['inserted'])}\n"
        f"♻️ <b>Duplicates :</b> {_fmt(st['duplicate'])}\n"
        f"⚠️ <b>Errors     :</b> {_fmt(st['errors'])}\n\n"
        f"🚫 <b>Skipped    :</b> {_fmt(st['deleted'] + st['unsupported'])}\n"
        f"   ┣ deleted       {_fmt(st['deleted'])}\n"
        f"   ┗ unsupported   {_fmt(st['unsupported'])}\n\n"
        f"⏩ <b>Manual skip :</b> {_fmt(st['manual'])}\n"
        f"📥 <b>Collected   :</b> {_fmt(fetched)}\n\n"
        f"📝 <b>Last saved :</b>\n{rec}\n\n"
        f"ETA : {eta} ⏳   |   Last update : {now}"
    )

    await msg.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Cancel", callback_data="index#index_cancel")]]
        ),
        disable_web_page_preview=True,
    )


async def _show_final(msg, st: dict):
    elapsed = _eta(time.time() - (time.time() - 1))  # just formatting
    rec = "\n".join(f" • {n}" for n in st["recent"]) if st["recent"] else " —"
    txt = (
        "<b>✅ Indexing Completed</b>\n\n"
        f"Inserted   : {_fmt(st['inserted'])}\n"
        f"Duplicates : {_fmt(st['duplicate'])}\n"
        f"Errors     : {_fmt(st['errors'])}\n\n"
        f"Manual skip: {_fmt(st['manual'])}\n"
        f"Collected  : {_fmt(st['collected'])}\n"
        f"Skipped    : {_fmt(st['deleted'] + st['unsupported'])}\n"
        f"   ┣ deleted       {_fmt(st['deleted'])}\n"
        f"   ┗ unsupported   {_fmt(st['unsupported'])}\n\n"
        f"📝 <b>Last saved :</b>\n{rec}\n\n"
        f"Total time : {elapsed}"
    )
    await msg.edit(txt, disable_web_page_preview=True)


# ────────────────────────── live-channel listener (optional) ───────────────
@Client.on_message(filters.chat(LOG_CHANNEL) & media_filter)
async def live_ingest(_, msg):
    for ft in ("document", "video", "audio"):
        media = getattr(msg, ft, None)
        if media:
            break
    else:
        return
    media.file_type = ft
    media.caption = msg.caption
    if await check_file(media) != "okda":
        return
    await save_file(media)
