import time
import random
from pyrogram.types import Message
from pyrogram import Client, filters, enums
from info import UPDATES_CHANNEL, LATEST_UPLOADS, MOVIE_GROUP, MOVIE_BOT
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

CMD = ["/", "."]

HELP_TXT = """<b>Bro, Check Movie Name In #Google and Try ! Then No Results Add Movie Year and Try , Again No Results ? It's Not Available In Our Database Or Movie Not Released !\n\nബ്രോ, മൂവിയുടെ പേര് മാത്രം #Google നോക്കിയിട്ട് അടിച്ചു നോക്കുക..!!\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ പേരിന്റെ കൂടെ മൂവി ഇറങ്ങിയ വർഷം കൂടി അടിച്ചു നോക്ക് 😁\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ ആ മൂവി ഞങ്ങളുടെ ഡാറ്റാബേസിൽ ഇല്ല, അല്ലെങ്കിൽ ആ മൂവി ഇറങ്ങിയിട്ടില്ല എന്ന് മനസ്സിലാക്കുക! 🤗⚠️\n\n📌 𝖢𝗁𝖾𝖼𝗄 𝖳𝗎𝗍𝗈𝗋𝗂𝖺𝗅 𝖵𝗂𝖽𝖾𝗈 𝖡𝗒 /Tutorial 𝖢𝗈𝗆𝗆𝖺𝗇𝖽 🤗.</b>"""

links_btn = [
    [
        InlineKeyboardButton(text = 'ʙᴏᴛ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ', url = f"{UPDATES_CHANNEL}")
    ],
    [
        InlineKeyboardButton(text = 'ᴍᴏᴠɪᴇ ꜱᴇᴀʀᴄʜ ɢʀᴏᴜᴘ', url = f"{MOVIE_GROUP}")
    ],
    [
        InlineKeyboardButton(text = 'ᴍᴏᴠɪᴇ ꜱᴇᴀʀᴄʜ ʙᴏᴛ', url = f"{MOVIE_BOT}")
    ],
    [
        InlineKeyboardButton(text = 'ʟᴀᴛᴇꜱᴛ ᴜᴘʟᴏᴀᴅꜱ ᴄʜᴀɴɴᴇʟ', url = f"{LATEST_UPLOADS}")
    ]
]

@Client.on_message(filters.command(["links"]) & filters.private, group=1)
async def links(client, message):
    await message.reply_photo(
        photo="http://graph.org/file/8270c1de86b6a36255eaf.jpg",
        text="<b>🔗 𝖢𝗁𝖾𝖼𝗄 𝖮𝗎𝗍 𝖠𝗅𝗅 𝖮𝗎𝗋 𝖫𝗂𝗇𝗄𝗌 𝖥𝗋𝗈𝗆 𝗍𝗁𝖾 𝖡𝗎𝗍𝗍𝗈𝗇𝗌 𝖦𝗂𝗏𝖾𝗇 𝖡𝖾𝗅𝗈𝗐.\n\n© 𝖳𝖾𝖺𝗆 <a href='https://t.me/ProSearchFather'>@𝖯𝗋𝗈𝖲𝖾𝖺𝗋𝖼𝗁𝖥𝖺𝗍𝗁𝖾𝗋</a></b>",
        quote=True,
        reply_markup=InlineKeyboardMarkup(links_btn)
    )
    
@Client.on_message(filters.command(["help"]) & filters.private, group=1)
async def help(client, message):
    buttons = [[
            InlineKeyboardButton("🔒 𝖢𝗅𝗈𝗌𝖾 𝖳𝗁𝗂𝗌 𝖬𝖾𝗌𝗌𝖺𝗀𝖾 🔒", callback_data='close_data'),
        ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply_video(
        video="http://graph.org/file/d3900a6bc416c63d07973.mp4",
        caption="<b>Bro, Check Movie Name In #Google and Try ! Then No Results Add Movie Year and Try , Again No Results ? It's Not Available In Our Database Or Movie Not Released !\n\nബ്രോ, മൂവിയുടെ പേര് മാത്രം #Google നോക്കിയിട്ട് അടിച്ചു നോക്കുക..!!\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ പേരിന്റെ കൂടെ മൂവി ഇറങ്ങിയ വർഷം കൂടി അടിച്ചു നോക്ക് 😁\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ ആ മൂവി ഞങ്ങളുടെ ഡാറ്റാബേസിൽ ഇല്ല, അല്ലെങ്കിൽ ആ മൂവി ഇറങ്ങിയിട്ടില്ല എന്ന് മനസ്സിലാക്കുക! 🤗⚠️\n\n📌 𝖢𝗁𝖾𝖼𝗄 𝖳𝗎𝗍𝗈𝗋𝗂𝖺𝗅 𝖵𝗂𝖽𝖾𝗈 𝖡𝗒 /Tutorial 𝖢𝗈𝗆𝗆𝖺𝗇𝖽 🤗.</b>",
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML,
        reply_to_message_id=message.id
    )
    
@Client.on_message(filters.command(["tutorial"]) & filters.private, group=1)
async def tutorial(client, message):
    buttons = [[
            InlineKeyboardButton("🔒 𝖢𝗅𝗈𝗌𝖾 𝖳𝗁𝗂𝗌 𝖬𝖾𝗌𝗌𝖺𝗀𝖾 🔒", callback_data='close_data'),
        ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply_video(
        video="http://graph.org/file/1802f90277bae20e9bc13.mp4",
        caption="<b>𝖶𝖺𝗍𝖼𝗁 𝖳𝗁𝗂𝗌 𝖳𝗎𝗍𝗈𝗋𝗂𝖺𝗅 𝖵𝗂𝖽𝖾𝗈 𝖳𝗈 𝖬𝖺𝗄𝖾 𝖬𝗒 𝖴𝗌𝖺𝗀𝖾 𝖤𝖺𝗌𝗂𝖾𝗋 𝖳𝗈 𝖸𝗈𝗎.\n\n𝖳𝖾𝖺𝗆 @ProSearchFather .</b>",
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML,
        reply_to_message_id=message.id
    )
    
@Client.on_message(filters.group & filters.incoming)
async def grp(_,message: Message):
    buttons = [[
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴏᴜʀ ʙᴏᴛ ᴛᴏ ᴛʜɪꜱ ɢʀᴏᴜᴘ ➕", url='http://t.me/Bae_Suzzy_Bot?startgroup=true'),
        ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply_video(
        video="http://graph.org/file/d3900a6bc416c63d07973.mp4",
        caption="<b> ⚠️ You can't Use @ProSearchFatherBot in Groups for Searching Movies/Series!\n\nYou Can Use @Bae_Suzzy_Bot for Searching Files in Groups Easily, @ProSearchFatherBot is Specially Designed For PM Search..\n\n Team @ProSearchFather !</b>",
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML,
        reply_to_message_id=message.id
    )
    
@Client.on_message(filters.command("about", CMD))
async def check_about(_, message):
    await message.reply_text("<b>@ProSearchFather is a Movie / Series Searching Telegram Project!\n\nThanks to all who made efforts to build this project.</b>")
    
@Client.on_message(filters.command("ping", CMD))
async def ping(_, message):
    start_t = time.time()
    rm = await message.reply_text("...")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await rm.edit(f"Pong!\n{time_taken_s:.3f} ms")
