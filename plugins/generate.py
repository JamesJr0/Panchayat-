#© 𝘼𝙗𝙊𝙪𝙩𝙈𝙚_𝘿𝙆

import re
import os
import logging
import asyncio
import datetime
import html
from bs4 import BeautifulSoup
from pyrogram import Client, filters, enums
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GENLINK_CHANNEL = -1002200072223
chat_id_dict = {}
file_id_dict = {}
forwarded_messages = {}
initial_message_ids = {}
last_link_time = {}

async def handle_file(c: Client, query: CallbackQuery, file_id: str, file_type: str):
    user_id = query.from_user.id
    try:
        forwarded_msg = await c.copy_message(chat_id=GENLINK_CHANNEL, from_chat_id=query.message.chat.id, message_id=query.message.id)
        forwarded_messages[forwarded_msg.id] = user_id
        initial_message_ids[forwarded_msg.id] = query.message.id
        last_link_time[user_id] = datetime.datetime.now()
    except FloodWait as e:
        await asyncio.sleep(e.x)
        forwarded_msg = await c.copy_message(chat_id=GENLINK_CHANNEL, from_chat_id=query.message.chat.id, message_id=query.message.id)
        forwarded_messages[forwarded_msg.id] = user_id
        initial_message_ids[forwarded_msg.id] = query.message.id
        last_link_time[user_id] = datetime.datetime.now()

@Client.on_callback_query(filters.regex(r'^generate$'))
async def generate_link(c: Client, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id_dict[user_id] = query.message.chat.id
    initial_message = query.message
    if user_id in last_link_time:
        last_link_generation_time = last_link_time[user_id]
        time_diff = datetime.datetime.now() - last_link_generation_time
        if time_diff.total_seconds() < 30:
            await query.answer("Kindly wait for {} seconds to generate link for this file.".format(30 - int(time_diff.total_seconds())), show_alert=True)
            return
    await query.answer("🔗 Generating Your Link, Check File Caption ✅", show_alert=True)
    if query.message.document:
        file_id = query.message.document.file_id
        file_id_dict[file_id] = user_id
        await handle_file(c, query, file_id, 'document')
    elif query.message.video:
        file_id = query.message.video.file_id
        file_id_dict[file_id] = user_id
        await handle_file(c, query, file_id, 'video')
    else:
        print("<b><i>ഊമ്പി 🙃</b></i>")
        return

  @Client.on_message(filters.chat(GENLINK_CHANNEL) & filters.reply)
async def return_link(c: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.id in forwarded_messages:
        user_id = forwarded_messages[message.reply_to_message.id]
        initial_message_id = initial_message_ids[message.reply_to_message.id]
        html_text = message.text
        soup = BeautifulSoup(html_text, 'html.parser')
        links = [a.get('href') for a in soup.find_all('a', href=True)]
        if message.reply_to_message and message.reply_to_message.caption:
            original_text = message.reply_to_message.caption
            custom_message = "**✅ Fast Direct Download Link Generated, Click The Button Below:**"
            new_text = f"**{original_text}**\n\n{custom_message}"
        else:
            original_text = ""
            new_text = custom_message
        if len(links) == 2:
            link1, link2 = links
            button1 = InlineKeyboardButton("Link 1", url=link1)
            button2 = InlineKeyboardButton("Link 2", url=link2)
            keyboard = InlineKeyboardMarkup([[button1, button2]])
        else:
            custom_message = "\n<b>❌ Failed to generate download link!</b>"
            keyboard = None
        await c.edit_message_text(chat_id=chat_id_dict[user_id], message_id=initial_message_id, text=new_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=keyboard)
            
