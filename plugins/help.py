import time
import random
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client, filters

CMD = ["/", "."]

@Client.on_message(filters.command("help", CMD))
async def check_alive(_, message):
    await message.reply_text("<b>Bro, Check Movie Name In #Google and Try ! Then No Results Add Movie Year and Try , Again No Results ? It's Not Available In Our Database Or Movie Not Released !\n\nബ്രോ, മൂവിയുടെ പേര് മാത്രം #Google നോക്കിയിട്ട് അടിച്ചു നോക്കുക..!!\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ പേരിന്റെ കൂടെ മൂവി ഇറങ്ങിയ വർഷം കൂടി അടിച്ചു നോക്ക് 😁\n\nഎനിയും കിട്ടിയില്ലെങ്കിൽ ആ മൂവി ഞങ്ങളുടെ ഡാറ്റാബേസിൽ ഇല്ല, അല്ലെങ്കിൽ ആ മൂവി ഇറങ്ങിയിട്ടില്ല എന്ന് മനസ്സിലാക്കുക! 🤗⚠️\n\n📌 Any Help For Movie Searching Contact Admin.</b>")
    buttons = [
            [
                InlineKeyboardButton('🌿 Jᴏɪɴ Fᴏʀ Mᴏʀᴇ 🌿', url='https://t.me/cpflicks')
            ],
            [
                InlineKeyboardButton('🔒 𝖢𝗅𝗈𝗌𝖾 𝖳𝗁𝗂𝗌 𝖬𝖾𝗌𝗌𝖺𝗀𝖾 🔒', callback_data='close_data'),
            ]
            ]
        reply_markup = InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command("ping", CMD))
async def ping(_, message):
    start_t = time.time()
    rm = await message.reply_text("...")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await rm.edit(f"Pong!\n{time_taken_s:.3f} ms")
