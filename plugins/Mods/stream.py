#created by @lallu_tg
#use with proper credits



import asyncio
import urllib.parse
from Lallus.database import Database
from Lallus.human_readable import humanbytes
from Lallus.vars import Var
from info import BIN_CHANNEL, UPDATES_CHANNEL, SESSION_NAME
from pyrogram import filters, Client
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums.parse_mode import ParseMode
db = Database(Var.DATABASE_URL, SESSION_NAME)


def get_media_file_size(m):
    media = m.video or m.audio or m.document
    if media and media.file_size:
        return media.file_size
    else:
        return None


def get_media_file_name(m):
    media = m.video or m.document or m.audio
    if media and media.file_name:
        return urllib.parse.quote_plus(media.file_name)
    else:
        return None


@Client.on_message(filters.private & (filters.command("getlink")))
async def private_receive_handler(client, m:Message):
          
    if not m.reply_to_message and not m.reply_to_message.media:
          return await m.reply("⚠️ 𝖴𝗌𝖾 𝖳𝗁𝗂𝗌 𝖢𝗈𝗆𝗆𝖺𝗇𝖽 𝖠𝗌 𝖱𝖾𝗉𝗅𝗒 𝖳𝗈 𝖠𝗇𝗒 𝖠𝗎𝖽𝗂𝗈 / 𝖵𝗂𝖽𝖾𝗈 / 𝖣𝗈𝖼𝗎𝗆𝖾𝗇𝗍 𝖳𝗈 𝖦𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝖨𝗇𝗌𝗍𝖺𝗇𝗍 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝖫𝗂𝗇𝗄 !")
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await client.send_message(
            BIN_CHANNEL,
            f"Nᴇᴡ Usᴇʀ Jᴏɪɴᴇᴅ : \n\nNᴀᴍᴇ : [{m.from_user.first_name}](tg://user?id={m.from_user.id}) Sᴛᴀʀᴛᴇᴅ Yᴏᴜʀ Bᴏᴛ !!"
        )
    try:
        log_msg = await m.reply_to_message.forward(chat_id=BIN_CHANNEL)
        file_name = get_media_file_name(m.reply_to_message)
        file_size = humanbytes(get_media_file_size(m.reply_to_message))
        stream_link = "https://{}/{}/{}".format(Var.FQDN, log_msg.id, file_name) if Var.ON_HEROKU or Var.NO_PORT else \
            "http://{}:{}/{}/{}".format(Var.FQDN,
                                    Var.PORT,
                                    log_msg.id,
                                    file_name)

        msg_text ="""
<i><u>🔗 Yᴏᴜʀ Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ 😜</u></i>\n
<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <b><i>{}</b></i>\n
<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <b><i>{}</b></i>\n
<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <b><i>{}</b></i>\n
<b>🚀 Cᴏᴘʏ ᴀɴᴅ Pᴀꜱᴛᴇ Tʜɪꜱ Lɪɴᴋ ɪɴ Yᴏᴜʀ Bʀᴏᴡꜱᴇʀ ᴀɴᴅ ᴛʜᴇ Fɪʟᴇ Dᴏᴡɴʟᴏᴀᴅ Wɪʟʟ Sᴛᴀʀᴛ Iᴍᴍᴇᴅɪᴀᴛᴇʟʏ!!</b>\n
<b><i>© @CpFlicks</b></i>"""

        await log_msg.reply_text(text=f"**RᴇQᴜᴇꜱᴛᴇᴅ ʙʏ :** [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n**Uꜱᴇʀ ɪᴅ :** `{m.from_user.id}`\n**Dᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ :** {stream_link}", disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN, quote=True)
        await m.reply_text(
            text=msg_text.format(file_name, file_size, stream_link),
            parse_mode=ParseMode.HTML, 
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋ 📥", url=stream_link)]]),
            quote=True
        )
    except FloodWait as e:
        print(f"Sleeping for {str(e.value)}s")
        await asyncio.sleep(e.value)
        await client.send_message(chat_id=Var.BIN_CHANNEL, text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(e.value)}s from [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n\n**𝚄𝚜𝚎𝚛 𝙸𝙳 :** `{str(m.from_user.id)}`", disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)


@Client.on_message(filters.channel & (filters.document | filters.video), group=-1)
async def channel_receive_handler(bot, broadcast):
    if int(broadcast.chat.id) in Var.BANNED_CHANNELS:
        await bot.leave_chat(broadcast.chat.id)
        return
    try:
        log_msg = await broadcast.forward(chat_id=Var.BIN_CHANNEL)
        stream_link = "https://{}/{}".format(Var.FQDN, log_msg.id) if Var.ON_HEROKU or Var.NO_PORT else \
            "http://{}:{}/{}".format(Var.FQDN,
                                    Var.PORT,
                                    log_msg.id)
        await log_msg.reply_text(
            text=f"**Cʜᴀɴɴᴇʟ Nᴀᴍᴇ:** `{broadcast.chat.title}`\n**Cʜᴀɴɴᴇʟ ID:** `{broadcast.chat.id}`\n**Rᴇǫᴜᴇsᴛ ᴜʀʟ:** https://t.me/{(await bot.get_me()).username}?start=AvishkarPatil_{str(log_msg.id)}",
            # text=f"**Cʜᴀɴɴᴇʟ Nᴀᴍᴇ:** `{broadcast.chat.title}`\n**Cʜᴀɴɴᴇʟ ID:** `{broadcast.chat.id}`\n**Rᴇǫᴜᴇsᴛ ᴜʀʟ:** https://t.me/FxStreamBot?start=AvishkarPatil_{str(log_msg.id)}",
            quote=True,
            parse_mode=ParseMode.MARKDOWN
        )
        await bot.edit_message_reply_markup(
            chat_id=broadcast.chat.id,
            message_id=broadcast.id,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Dᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ 📥", url=f"https://t.me/botechs_bot?start=AvishkarPatil_{str(log_msg.id)}")]])
            # [[InlineKeyboardButton("Dᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋ 📥", url=f"https://t.me/botechs_bot?start=AvishkarPatil_{str(log_msg.id)}")]])
        )
    except FloodWait as w:
        print(f"Sleeping for {str(w.value)}s")
        await asyncio.sleep(w.value)
        await bot.send_message(chat_id=Var.BIN_CHANNEL,
                             text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(w.value)}s from {broadcast.chat.title}\n\n**Cʜᴀɴɴᴇʟ ID:** `{str(broadcast.chat.id)}`",
                             disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await bot.send_message(chat_id=Var.BIN_CHANNEL, text=f"**#ᴇʀʀᴏʀ_ᴛʀᴀᴄᴇʙᴀᴄᴋ:** `{e}`", disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
        print(f"Cᴀɴ'ᴛ Eᴅɪᴛ Bʀᴏᴀᴅᴄᴀsᴛ Mᴇssᴀɢᴇ!\nEʀʀᴏʀ: {e}")
