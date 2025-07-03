# script.py
# (Or whatever file contains your script class and possibly other handlers)

import asyncio
import time # Needed for _h helper if not already defined globally or imported

from pyrogram import Client, filters
# Import the new count functions from your database module
from database.ia_filterdb import (
    get_total_files_count,
    get_files_count_db1,
    get_files_count_db2,
    get_files_count_db3,
    get_files_count_db4,
    get_users_count,
    get_chats_count
)

# You will need to import ADMINS from info.py or define it here if it's not global
from info import ADMINS # Removed BOT_USERNAME import

class script(object):
    START_TXT = """<b>𝖧𝖾𝗒 {},\n\n𝖨 𝖺𝗆 𝖠 𝖥𝗂𝗅𝗍𝖾𝗋 𝖡𝗈𝗍 𝖮𝖿𝖿𝗂𝖼𝗂𝖺𝗅𝗅𝗒 𝖬𝖺𝖽𝖾 B𝗒 𝖳𝖾𝖺𝗆 <a href='https://t.me/ProSearchFather'>@𝖯𝗋𝗈𝖲𝖾𝖺𝗋𝖼𝗁𝖥𝖺𝗍𝗁𝖾𝗋</a>.\n\n𝖧𝖾𝗋𝖾 𝖸𝗈𝗎 𝖢𝖺𝗇 𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝖬𝗈𝗏𝗂𝖾/𝖲𝖾𝗋𝗂𝖾𝗌, 𝖩𝗎𝗌𝗍 𝖲𝖾𝗇𝗍 𝖬𝗈𝗏𝗂𝖾/𝖲𝖾𝗋𝗂𝖾𝗌 𝖭𝖺𝗆𝖾 𝖶𝗂𝗍𝗁 𝖯𝗋𝗈𝗉𝖾𝗋 <a href='https://www.google.com/'>𝖦𝗈𝗈𝗀𝗅𝖾</a> 𝖲𝗉𝖾𝗅𝗅𝗂𝗇𝗀..!!\n\nFᴏʀ Mᴏʀᴇ Dᴇᴛᴀɪʟꜱ Cʟɪᴄᴋ /help\n\n𝖢𝗁𝖾𝖼𝗄 𝖮𝗎𝗍 𝖠𝗅𝗅 𝖮𝗎𝗋 𝖫𝗂𝗇𝗄𝗌 /links</b>"""
    LINKS_TXT = """<b>🔗 𝖢𝗁𝖾𝖼𝗄 𝖮𝗎𝗍 𝖠𝗅𝗅 𝖮𝗎𝗋 𝖫𝗂𝗇𝗄𝗌 𝖥𝗋𝗈𝗆 𝗍𝗁𝖾 𝖡𝗎𝗍𝗍𝗈𝗇𝗌 𝖦𝗂𝗏𝖾𝗇 𝖡𝖾𝗅𝗈𝗐.\n\n© 𝖳𝖾𝖺𝗆 <a href='https://t.me/ProSearchFather'>@𝖯𝗋𝗈𝖲𝖾𝖺𝗋𝖼𝗁𝖥𝖺𝗍𝗁𝖾𝗋</a></b>"""
    HELP_TXT = """<b>Bro, Check Movie Name In #Google and Try ! Then No Results Add Movie Year and Try , Again No Results ? It's Not Available In Our Database Or Movie Not Released !\n\nബ്രോ, മൂവിയുടെ പേര് മാത്രം #Google നോക്കിയിട്ട് അടിച്ചു നോക്കുക..!!\n\nഎന്നിട്ടും കിട്ടിയില്ലെങ്കിൽ പേരിന്റെ കൂടെ മൂവി ഇറങ്ങിയ വർഷം കൂടി അടിച്ചു നോക്ക് 😁\n\nഎനിയും കിട്ടിയില്ലെങ്കിൽ ആ മൂവി ഞങ്ങളുടെ ഡാറ്റാബേസിൽ ഇല്ല, അല്ലെങ്കിൽ ആ മൂവി ഇറങ്ങിയിട്ടില്ല എന്ന് മനസ്സിലാക്കുക! 🤗⚠️\n\n📌 Any Help For Movie Searching Contact Admin.</b>"""
    ABOUT_TXT = """<b>👋 Hello,</b>
<b>👤 My Name:</b> ProSearch
<b>🧑‍💻 Creator:</b> <a href='https://t.me/Luffy_Krishna'>YiFaN ♥️</a>
<b>📱 Language:</b> Python 3
<b>📚 Library:</b> Pyrogram Asyncio 0.18.1
<b>🔐 Database:</b> <a href='https://www.mongodb.com'>MongoDB Free Tier</a>
<b>⚡ Server:</b> Contabo
<b>🛠 Status:</b> V9.8 [Beta]</b>"""

    ENGLISHSPELL_TXT = """<b>‼️ FILE NOT FOUND  ‼️\n\n1️⃣ സിനിമയുടെ സ്പെല്ലിങ്ങ് ഗൂഗിളിൽ ഉള്ളത് പോലെ ആണോ നിങ്ങൾ അടിച്ചത് എന്ന് ഉറപ്പ് വരുത്തുക..!!\n\n2️⃣ നിങ്ങൾ ചോദിച്ച സിനിമ OTT റിലീസ് ആയതാണോ എന്ന് ചെക്ക് ചെയ്യുക..!!\n\n3️⃣ സഹായം ആവശ്യമുള്ളവർ <a href='https://t.me/+iqUWSdGIMOw3NGM1'>പ്രോസെർച്ച് സപ്പോർട്ട്</a> ഗ്രൂപ്പുമായി ബന്ധപ്പെടുക അഡ്മിൻസ് സഹായിക്കുന്നതാണ്.\n\n4️⃣ 𝖢𝗈𝗇𝗍𝖺𝖼𝗍 𝖠𝖽𝗆𝗂𝗇𝗌, 𝖲𝗈 𝖳𝗁𝖾𝗒 𝖢𝖺𝗇 𝖠𝖽𝖽 𝖥𝗂𝗅𝖾𝗌 𝖳𝗈 𝖬𝗒 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾 !</b>"""
    SUZZY_TXT = """<b> ⚠️ You can't Use @ProSearchFatherBot in Groups for Searching Movies/Series!\n\nYou Can Use @ProSearchMoviez_Bot for Searching Files in Groups Easily, @ProSearchFatherBot is Specially Designed For PM Search..\n\n Team @ProSearchFather !</b>"""
    SOURCE_TXT = """<b>NOTE:</b>
- ഇപ്പൊ കിട്ടും നോക്കി ഇരുന്നോ .
<b>DEVS:</b>
- <a href=https://t.me/AboutMe_DK>Dᴋ</a>"""
    MANUELFILTER_TXT = """ʜᴇʟᴘ: <b>ꜰɪʟᴛᴇʀꜱ</b>
- ꜰɪʟᴛᴇʀ ɪꜱ ᴀ ꜰᴇᴀᴛᴜʀᴇ ᴡᴇʀᴇ ᴜꜱᴇʀꜱ ᴄᴀɴ ꜱᴇᴛ ᴀᴜᴛᴏᴍᴀᴛᴇᴅ ʀᴇᴘʟɪᴇꜱ ꜰᴏʀ ᴀ ᴘᴀʀᴛɪᴄᴜʟᴀʀ ᴋᴇʏᴡᴏʀᴅ ᴀɴᴅ ɪ ᴡɪʟʟ ʀᴇꜱᴘᴏɴᴅ ᴡʜᴇɴᴇᴠᴇʀ ᴀ ᴋᴇʏᴡᴏʀᴅ ɪꜱ ꜰᴏᴜɴᴅ ɪɴ ᴛʜᴇ ᴍᴇꜱꜱᴀɢᴇ

<b>ɴᴏᴛᴇ:</b>
1.🛑 ᴛʜɪꜱ ʙᴏᴛ ꜱʜᴏᴜʟᴅ ʜᴀᴠᴇ ᴀᴅᴍɪɴ ᴘʀɪᴠɪʟᴇɢᴇ.
2.🛑 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴀᴅᴅ ꜰɪʟᴛᴇʀꜱ ɪɴ ᴀ ᴄʜᴀᴛ.
3.🛑ᴀʟᴇʀᴛ ʙᴜᴛᴛᴏɴꜱ ʜᴀᴠᴇ ᴀ ʟɪᴍɪᴛ ᴏꜰ 64 ᴄʜᴀʀᴀᴄᴛᴇʀꜱ.

Cᴏᴍᴍᴀɴᴅs Aɴᴅ Usᴀɢᴇ:
• /filter - <code>ᴀᴅᴅ ᴀ ꜰɪʟᴛᴇʀ ɪɴ ᴀ ᴄʜᴀᴛ ♾️</code>
• /filters - <code>ʟɪꜱᴛ ᴀʟʟ ᴛʜᴇ ꜰɪʟᴛᴇʀꜱ ᴏꜰ ᴀ ᴄʜᴀᴛ♾️</code>
• /del - <code>ᴅᴇʟᴇᴛᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ꜰɪʟᴛᴇʀ ɪɴ ᴀ ᴄʜᴀᴛ♾️</code>
• /delall - <code>ᴅᴇʟᴇᴛᴇ ᴛʜᴇ ᴡʜᴏʟᴇ ꜰɪʟᴛᴇʀꜱ ɪɴ ᴀ ᴄʜᴀᴛ (ᴄʜᴀᴛ ᴏᴡɴᴇʀ ᴏɴʟʏ)♾️</code>"""
    BUTTON_TXT = """Help: <b>Buttons</b>
ɪ ᴄᴀɴ ꜱᴜᴘᴘᴏʀᴛ ʙᴏᴛʜ ᴜʀʟ ᴀɴᴅ ᴀʟᴇʀᴛ ɪɴʟɪɴᴇ ʙᴜᴛᴛᴏɴꜱ 🎬🪄

<b>NOTE:</b>
1. ᴛᴇʟᴇɢʀᴀᴍ ᴡɪʟʟ ɴᴏᴛ ᴀʟʟᴏᴡꜱ ʏᴏᴜ ᴛᴏ ꜱᴇɴᴅ ʙᴜᴛᴛᴏɴꜱ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴄᴏɴᴛᴇɴᴛ, ꜱᴏ ᴄᴏɴᴛᴇɴᴛ ɪꜱ ᴍᴀɴᴅᴀᴛᴏʀʏ.
2. ᴛʜɪꜱ ʙᴏᴛ ꜱᴜᴘᴘᴏʀᴛꜱ ʙᴜᴛᴛᴏɴꜱ ᴡɪᴛʜ ᴀɴʏ ᴛᴇʟᴇɢʀᴀᴍ ᴍᴇᴅɪᴀ ᴛʏᴘᴇ.
3. ʙᴜᴛᴛᴏɴꜱ ꜱʜᴏᴜʟᴅ ʙᴇ ᴘʀᴏᴘᴇʀʟʏ ᴘᴀʀꜱᴇᴅ ᴀꜱ ᴍᴀʀᴋᴅᴏᴡɴ ꜰᴏʀᴍᴀᴛ

<b>URL buttons:</b>
<code>[Button Text](buttonurl:https://t.me/ProSearchMoviez_bot)</code>

<b>Alert buttons:</b>
<code>[Button Text](buttonalert:This is an alert message)</code>"""
    AUTOFILTER_TXT = """ʜᴇʟᴘ: <b>ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ</b>
<b>ɴᴏᴛᴇ: Fɪʟᴇ Iɴᴅᴇx</b>
1. ᴍᴀᴋᴇ ᴍᴇ ᴛʜᴇ ᴀᴅᴍɪɴ ᴏꜰ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ɪꜰ ɪᴛ'ꜱ ᴘʀɪᴠᴀᴛᴇ.
2. ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴀᴛ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴅᴏᴇꜱ ɴᴏᴛ ᴄᴏɴᴛᴀɪɴꜱ ᴄᴀᴍʀɪᴘꜱ, ᴘᴏʀɴ ᴀɴᴅ ꜰᴀᴋᴇ ꜰɪʟᴇꜱ.
3. ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ʟᴀꜱᴛ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴍᴇ ᴡɪᴛʜ Qᴜᴏᴛᴇꜱ. ɪ'ʟʟ ᴀᴅᴅ ᴀʟʟ ᴛʜᴇ ꜰɪʟᴇꜱ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴍʏ ᴅʙ.

<b>Nᴏᴛᴇ: AᴜᴛᴏFɪʟᴛᴇʀ</b>
1. Aᴅᴅ ᴛʜᴇ ʙᴏᴛ ᴀs ᴀᴅᴍɪɴ ᴏɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ.
2. Usᴇ /connect ᴀɴᴅ ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴛᴏ ᴛʜᴇ ʙᴏᴛ.
3. Usᴇ /settings ᴏɴ ʙᴏᴛ's PM ᴀɴᴅ ᴛᴜʀɴ ᴏɴ AᴜᴛᴏFɪʟᴛᴇʀ ᴏɴ ᴛʜᴇ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ."""
    CONNECTION_TXT = """ʜᴇʟᴘ: <b>ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ</b>
- ᴜꜱᴇᴅ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ ʙᴏᴛ ᴛᴏ ᴘᴍ ꜰᴏʀ ᴍᴀɴᴀɢɪɴɢ ꜰɪʟᴛᴇʀꜱ
- ɪᴛ ʜᴇʟᴘꜱ ᴛᴏ ᴀᴠᴏɪᴅ ꜱᴘᴀᴍᴍɪɴɢ ɪɴ ɢʀᴏᴜᴘꜱ.
<b>ɴᴏᴛᴇ:</b>

1. ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴀᴅᴅ ᴀ ᴄᴏɴɴᴇᴄᴛɪᴏɴ.
2. ꜱᴇɴᴅ <code>/ᴄᴏɴɴᴇᴄᴛ</code> ꜰᴏʀ ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ᴘᴍ

Cᴏᴍᴍᴀɴᴅs Aɴᴅ Usᴀɢᴇ:
• /connect  - <code>ᴄᴏɴɴᴇᴄᴛ ᴀ ᴘᴀʀᴛɪᴄᴜʟᴀʀ ᴄʜᴀᴛ ᴛᴏ ʏᴏᴜʀ ᴘᴍ</code>
• /disconnect  - <code>ᴅɪꜱᴄᴏɴɴᴇᴄᴛ ꜰʀᴏᴍ ᴀ ᴄʜᴀᴛ</code>
• /connections - <code>ʟɪꜱᴛ ᴀʟʟ ʏᴏᴜʀ ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ</code>"""
    EXTRAMOD_TXT = """ʜᴇʟᴘ: Exᴛʀᴀ MᴏᴅᴜʟᴇS
<b>ɴᴏᴛᴇ:</b>

🏹ᴛʜᴇꜱᴇ ᴀʀᴇ ᴛʜᴇ ᴇxᴛʀᴀ ꜰᴇᴀᴛᴜʀᴇꜱ ᴏꜰ ᴛʜɪꜱ ʙᴏᴛ

Cᴏᴍᴍᴀɴᴅs Aɴᴅ Usᴀɢᴇ:
• /id - <code>ɢᴇᴛ ɪᴅ ᴏꜰ ᴀ ꜱᴘᴇᴄɪꜰɪᴇᴅ ᴜꜱᴇʀ.</code>
• /info  - <code>ɢᴇᴛ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴀ ᴜꜱᴇʀ.</code>
• /imdb  - <code>ɢᴇᴛ ᴛʜᴇ ꜰɪʟᴍ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ꜰʀᴏᴍ ɪᴍᴅʙ ꜱᴏᴜʀᴄᴇ.</code>
• /search  - <code>ɢᴇᴛ ᴛʜᴇ ꜰɪʟᴍ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ꜰʀᴏᴍ ᴠᴀʀɪᴏᴜꜱ ꜱᴏᴜʀᴄᴇꜱ.</code>"""
    ADMIN_TXT = """ʜᴇʟᴘ: Aᴅᴍɪɴ Mᴏᴅs
<b>ɴᴏᴛᴇ:</b>
Tʜɪs Mᴏᴅᴜʟᴇ Oɴʟʏ Wᴏʀks Fᴏʀ Mʏ Aᴅᴍɪɴs
Cᴏᴍᴍᴀɴᴅs Aɴᴅ Usᴀɢᴇ:
• /logs - <code>ᴛᴏ ɢᴇᴛ ᴛʜᴇ ʀᴇᴄᴇɴᴛ ᴇʀʀᴏʀꜱ</code>
• /msonedb - <code>ᴛᴏ ɢᴇᴛ ꜱᴛᴀᴛᴜꜱ ᴏꜰ ꜰɪʟᴇꜱ ɪɴ ᴅʙ. [Tʜɪs Cᴏᴍᴍᴀɴᴅ Cᴀɴ Bᴇ Usᴇᴅ Bʏ Aɴʏᴏɴᴇ]</code>
• /delete - <code>ᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ꜰɪʟᴇ ꜰʀᴏᴍ ᴅʙ.</code>
• /users - <code>ᴛᴏ ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴍʏ ᴜꜱᴇʀꜱ ᴀɴᴅ ɪᴅꜱ.</code>
• /chats - <code>ᴛᴏ ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴍʏ ᴄʜᴀᴛꜱ ᴀɴᴅ ɪᴅꜱ</code>
• /leave  - <code>ᴛᴏ ʟᴇᴀᴠᴇ ꜰʀᴏᴍ ᴀ ᴄʜᴀᴛ.</code>
• /disable  -  <code>ᴛᴏ ᴅɪꜱᴀʙʟᴇ ᴀ ᴄʜᴀᴛ.</code>
• /ban  - <code>ᴛᴏ ʙᴀɴ ᴀ ᴜꜱᴇʀ.</code>
• /unban  - <code>ᴛᴏ ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ.</code>
• /channel - <code>ᴛᴏ ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴛᴏᴛᴀʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴄʜᴀɴNELs</code>
• /broadcast - <code>ᴛᴏ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀꜱ</code>"""


    STATUS_TXT = """📂 𝖳𝗈𝗍𝖺𝗅 𝖥𝗂𝗅𝖾𝗌     - <code>{}</code>

👤 Users : <code>{}</code>
💬 Chats : <code>{}</code>

🗃️ DB 1 - <code>{}</code>
🗃️ DB 2 - <code>{}</code>
🗃️ DB 3 - <code>{}</code>
🗃️ DB 4 - <code>{}</code>
"""


    LOG_TEXT_G = """#NewGroup
Gʀᴏᴜᴘ = {}(<code>{}</code>)
Tᴏᴛᴀʟ Mᴇᴍʙᴇʀs = <code>{}</code>
Aᴅᴅᴇᴅ Bʏ - {}

@ProSearchFather"""

    LOG_TEXT_P = """#NewUser
ID - <code>{}</code>
Nᴀᴍᴇ - {}

@ProSearchFather"""

# Helper function for formatting numbers, defined here as per your structure
def _h(n: int) -> str:
    return f"{n:,}".replace(",", " ")

# The /stats command handler
@Client.on_message(filters.command("stats")) # Add & filters.user(ADMINS) if only for admins
async def send_stats_command(client: Client, message):
    # Fetch counts from the database
    total_files = await get_total_files_count()
    db1_count = await get_files_count_db1()
    db2_count = await get_files_count_db2()
    db3_count = await get_files_count_db3()
    db4_count = await get_files_count_db4()

    users_count = await get_users_count()
    chats_count = await get_chats_count()

    # Format the message using the STATUS_TXT template
    stats_message = script.STATUS_TXT.format(
        _h(total_files),
        _h(users_count),
        _h(chats_count),
        _h(db1_count),
        _h(db2_count),
        _h(db3_count),
        _h(db4_count)
    )

    await message.reply_text(stats_message)
