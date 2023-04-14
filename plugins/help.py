import time
import random
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

CMD = ["/", "."]

HELP_TXT = """<b>Bro, Check Movie Name In #Google and Try ! Then No Results Add Movie Year and Try , Again No Results ? It's Not Available In Our Database Or Movie Not Released !\n\nബ്രോ, മൂവിയുടെ പേര് മാത്രം #Google നോക്കിയിട്ട് അടിച്ചു നോക്കുക..!!\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ പേരിന്റെ കൂടെ മൂവി ഇറങ്ങിയ വർഷം കൂടി അടിച്ചു നോക്ക് 😁\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ ആ മൂവി ഞങ്ങളുടെ ഡാറ്റാബേസിൽ ഇല്ല, അല്ലെങ്കിൽ ആ മൂവി ഇറങ്ങിയിട്ടില്ല എന്ന് മനസ്സിലാക്കുക! 🤗⚠️\n\n📌 𝖢𝗁𝖾𝖼𝗄 𝖳𝗎𝗍𝗈𝗋𝗂𝖺𝗅 𝖵𝗂𝖽𝖾𝗈 𝖡𝗒 /Tutorial 𝖢𝗈𝗆𝗆𝖺𝗇𝖽 🤗.</b>"""


@Client.on_message(filters.command(["help"]) & filters.private, group=1)
async def help(client, message):
    buttons = [[
            InlineKeyboardButton('Start', callback_data='start'),
        ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await client.send_message(
        chat_id=message.chat.id,
        text=HELP_TXT,
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML,
        reply_to_message_id=message.id
    )

@Client.on_message(filters.command("tutorial", CMD))
async def check_tutorial(_, message):
    await message.reply_text("<b>𝖶𝖺𝗍𝖼𝗁 𝖳𝗁𝗂𝗌 𝖳𝗎𝗍𝗈𝗋𝗂𝖺𝗅 𝖵𝗂𝖽𝖾𝗈 𝖳𝗈 𝖬𝖺𝗄𝖾 𝖬𝗒 𝖴𝗌𝖺𝗀𝖾 𝖤𝖺𝗌𝗂𝖾𝗋 𝖸𝗈𝗎 : <a href='https://graph.org/file/b62314386a3ebdc1ed890.mp4'>𝖢𝗅𝗂𝖼𝗄 𝖧𝖾𝗋𝖾 !</a></b>")
                          
@Client.on_message(filters.command("ping", CMD))
async def ping(_, message):
    start_t = time.time()
    rm = await message.reply_text("...")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await rm.edit(f"Pong!\n{time_taken_s:.3f} ms")
