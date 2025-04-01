#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) @AlbertEinsteinTG

import asyncio
from pyrogram import Client, enums
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from database.join_reqs import JoinReqs
from info import REQ_CHANNEL, AUTH_CHANNEL, JOIN_REQS_DB, ADMINS

from logging import getLogger

logger = getLogger(__name__)
INVITE_LINK = None
db = JoinReqs

async def ForceSub(bot: Client, update: Message, file_id: str = False, mode="checksub"):
    """Forces users to join a channel before they can use the bot."""
    
    global INVITE_LINK
    auth = ADMINS.copy() + [1125210189]

    if update.from_user.id in auth:
        return True  # Admins are exempt

    if not AUTH_CHANNEL and not REQ_CHANNEL:
        return True

    is_cb = False
    if not hasattr(update, "chat"):
        update.message.from_user = update.from_user
        update = update.message
        is_cb = True

    try:
        # Create or refresh Invite Link
        if INVITE_LINK is None:
            invite_link = (await bot.create_chat_invite_link(
                chat_id=(int(AUTH_CHANNEL) if not REQ_CHANNEL and not JOIN_REQS_DB else REQ_CHANNEL),
                creates_join_request=True if REQ_CHANNEL and JOIN_REQS_DB else False
            )).invite_link
            INVITE_LINK = invite_link
            logger.info("Created/Refreshed Invite Link")
        else:
            invite_link = INVITE_LINK

    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await ForceSub(bot, update, file_id)

    except Exception as err:
        logger.exception(f"Error creating invite link: {err}")
        await update.reply(
            text="Something went wrong while generating the invite link.",
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return False

    # Main Subscription Check
    if REQ_CHANNEL and db().isActive():
        try:
            user = await db().get_user(update.from_user.id)
            if user and user["user_id"] == update.from_user.id:
                return True
        except Exception as e:
            logger.exception("Database Error:", exc_info=True)
            await update.reply(
                text="Something went wrong while checking your subscription.",
                parse_mode=enums.ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return False

    try:
        if not AUTH_CHANNEL:
            raise UserNotParticipant

        # Check if User is Already Joined
        user = await bot.get_chat_member(
            chat_id=(int(AUTH_CHANNEL) if not REQ_CHANNEL and not db().isActive() else REQ_CHANNEL),
            user_id=update.from_user.id
        )

        if user.status == "kicked":
            await bot.send_message(
                chat_id=update.from_user.id,
                text="Sorry, you are banned from using this bot.",
                parse_mode=enums.ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_to_message_id=update.message_id
            )
            return False
        else:
            # ✅ Delete Force Subscribe Message after user joins
            try:
                await bot.delete_messages(
                    chat_id=update.chat.id,
                    message_ids=[update.message_id]
                )
            except Exception as e:
                logger.warning(f"Failed to delete Force Subscribe message: {e}")

            return True

    except UserNotParticipant:
        text = """**𝗛𝗼𝗹𝗱 𝗨𝗽 𝗕𝘂𝗱𝗱𝘆!!

𝖶𝖾 𝖺𝗉𝗉𝗋𝖾𝖼𝗂𝖺𝗍𝖾 𝗒𝗈𝗎𝗋 𝖼𝗈𝗆𝗂𝗇𝗀 𝗍𝗈 𝗈𝗎𝗋 𝖻𝗈𝗍 , 𝖻𝗎𝗍 𝗒𝗈𝗎 𝗇𝖾𝖾𝖽 𝗍𝗈 𝖩𝗈𝗂𝗇 𝗈𝗎𝗋 𝗕𝗔𝗖𝗞𝗨𝗣 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 𝖳𝗁𝖾𝗇 𝖼𝗅𝗂𝖼𝗄 𝗈𝗇 𝗧𝗥𝗬 𝗔𝗚𝗔𝗜𝗡 𝖡𝗎𝗍𝗍𝗈𝗇 𝖳𝗈 𝗀𝖾𝗍 𝖿𝗂𝗅𝖾𝗌.**"""

        updates_channel_link = "https://t.me/+p0RB9_pSWnU2Nzll"  # Your invite link

buttons = [
    [InlineKeyboardButton("📢 𝗕𝗔𝗖𝗞𝗨𝗣 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 📢", url=invite_link)],
    [InlineKeyboardButton("🔄 Try Again 🔄", callback_data=f"{mode}#{file_id}")],
    [InlineKeyboardButton("📌 Updates Channel", url=updates_channel_link)]
]
        
        if file_id is False:
    buttons.pop()  # Ensure this line is indented properly

        if not is_cb:
            await update.reply(
                text=text,
                quote=True,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.MARKDOWN,
            )
        return False

    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await ForceSub(bot, update, file_id)

    except Exception as err:
        logger.exception(f"Subscription check failed: {err}")
        await update.reply(
            text="Something went wrong while checking your subscription.",
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return False


def set_global_invite(url: str):
    """Updates the global invite link."""
    global INVITE_LINK
    INVITE_LINK = url
