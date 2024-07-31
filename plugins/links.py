from pyrogram.types import Message
from pyrogram import Client, filters, enums
from info import UPDATES_CHANNEL, LATEST_UPLOADS, MOVIE_GROUP, MOVIE_BOT
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

CMD = ["/", "."]
CHANNEL_ID = -1002224909238

links_btn = [
    [
        InlineKeyboardButton("ʙᴏᴛ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ", url = f"{UPDATES_CHANNEL}")
    ],
    [
        InlineKeyboardButton("ᴍᴏᴠɪᴇ ꜱᴇᴀʀᴄʜ ɢʀᴏᴜᴘ", url = f"{MOVIE_GROUP}")
    ],
    [
        InlineKeyboardButton("ᴍᴏᴠɪᴇ ꜱᴇᴀʀᴄʜ ʙᴏᴛ", url = f"{MOVIE_BOT}")
    ],
    [
        InlineKeyboardButton("ʟᴀᴛᴇꜱᴛ ᴜᴘʟᴏᴀᴅꜱ ᴄʜᴀɴɴᴇʟ", url = f"{LATEST_UPLOADS}")
    ]  
]

@Client.on_message(filters.command("links", CMD))
async def linkslist(client: Client, message: Message):
    await message.reply_photo(
        photo="http://graph.org/file/8270c1de86b6a36255eaf.jpg",
        caption="<b>🔗 𝖢𝗁𝖾𝖼𝗄 𝖮𝗎𝗍 𝖠𝗅𝗅 𝖮𝗎𝗋 𝖫𝗂𝗇𝗄𝗌 𝖥𝗋𝗈𝗆 𝗍𝗁𝖾 𝖡𝗎𝗍𝗍𝗈𝗇𝗌 𝖦𝗂𝗏𝖾𝗇 𝖡𝖾𝗅𝗈𝗐.\n\n© 𝖳𝖾𝖺𝗆 <a href='https://t.me/ProSearchFather'>@𝖯𝗋𝗈𝖲𝖾𝖺𝗋𝖼𝗁𝖥𝖺𝗍𝗁𝖾𝗋</a></b>",
        reply_markup=InlineKeyboardMarkup(links_btn),
        parse_mode=enums.ParseMode.HTML,
        reply_to_message_id=message.id
    )


@Client.on_message(filters.command("latest") & filters.incoming)
async def give_latest(client: Client, message: Message):
    return await client.copy_message(message.chat.id, -1002224909238, 2, reply_to_message_id=message.id)
    
