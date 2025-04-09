import re
from os import environ
from os import getenv
from dotenv import load_dotenv

# load_dotenv("./config.env")

id_pattern = re.compile(r'^.\d+$')
def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

# Bot information
SESSION = environ.get('SESSION', 'Media_search')
API_ID = int(environ.get('API_ID', '543598'))
API_HASH = environ.get('API_HASH', '293325819bb390ea1d2c3d823fa8e9fa')
BOT_TOKEN = environ.get('BOT_TOKEN', '6960947964:AAH9r6Sch96KcakHiSUE0VvSQoCKbsJLhOM')


# Bot settings
CACHE_TIME = int(environ.get('CACHE_TIME', 300))
USE_CAPTION_FILTER = bool(environ.get('USE_CAPTION_FILTER', False))
PICS = (environ.get('PICS', 'https://graph.org/file/b7bfe0352ba19d3c0d21d.jpg')).split()
UPDATE_CHANNEL = int(environ. get('UPDATE_CHANNEL', '-1002043794899'))

# Admins, Channels & Users
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '2092454280 6646976956 567835245').split()]
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '-1001768927947').split()]
auth_users = [int(user) if id_pattern.search(user) else user for user in environ.get('AUTH_USERS', '567835245').split()]
AUTH_USERS = (auth_users + ADMINS) if auth_users else []
auth_grp = environ.get('AUTH_GROUP')
AUTH_GROUPS = [int(ch) for ch in auth_grp.split()] if auth_grp else None

# MongoDB information
USERS_DB = environ.get('USERS_DB', "")
FILES_DB1 = environ.get('FILES_DB1', "")
FILES_DB2 = environ.get('FILES_DB2', "")
FILES_DB3 = environ.get('FILES_DB3', "")
FILES_DB4 = environ.get('FILES_DB4', "")
DATABASE_NAME = environ.get('DATABASE_NAME', "shibhukabot")
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'shibubot')

# FSUB
auth_channel = environ.get('AUTH_CHANNEL')
AUTH_CHANNEL = int(auth_channel) if auth_channel and id_pattern.search(auth_channel) else None
# Set to False inside the bracket if you don't want to use Request Channel else set it to Channel ID
REQ_CHANNEL = environ.get("REQ_CHANNEL", False)
REQ_CHANNEL = int(REQ_CHANNEL) if REQ_CHANNEL and id_pattern.search(REQ_CHANNEL) else False
JOIN_REQS_DB = environ.get("JOIN_REQS_DB", USERS_DB)

# CHANNELS LIST KEYS
UPDATES_CHANNEL = environ.get('UPDATES_CHANNEL', "https://t.me/+6guhTe_AHh44ODY1")
MOVIE_GROUP = environ.get('MOVIE_GROUP', "https://t.me/+FTt3LaNOvYk1ZWY1")
LATEST_UPLOADS = environ.get('LATEST_UPLOADS', "https://t.me/+-a7Vk8PDrCtiYTA9")
MOVIE_BOT = environ.get('MOVIE_BOT', "http://t.me/ProSearchMoviez_bot?start=help")

# Others
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1002130571317'))
SUPPORT_CHAT = environ.get('SUPPORT_CHAT', 'DKBOTxCHATS')
P_TTI_SHOW_OFF = is_enabled((environ.get('P_TTI_SHOW_OFF', "False")), False)
IMDB = is_enabled((environ.get('IMDB', "True")), True)
SINGLE_BUTTON = is_enabled((environ.get('SINGLE_BUTTON', "True")), True)
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", "<b>{file_caption}\n\n➢Channel : <a href= https://t.me/+6guhTe_AHh44ODY1>@ProSearchFather</a></b>")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", "<b>Hey </b> 😍\n\n<b>𝖧𝖾𝗋𝖾 𝖨𝗌 𝖶𝗁𝖺𝗍 𝖨 𝖥𝗈𝗎𝗇𝖽 𝖥𝗈𝗋 𝖸𝗈𝗎𝗋 𝖰𝗎𝖾𝗋𝗒 : <quote> {search} </quote> </b> 👇")
LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "False"), False)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "True"), True)
MAX_LIST_ELM = environ.get("MAX_LIST_ELM", None)
INDEX_REQ_CHANNEL = int(environ.get('INDEX_REQ_CHANNEL', LOG_CHANNEL))
FILE_STORE_CHANNEL = [int(ch) for ch in (environ.get('FILE_STORE_CHANNEL', '')).split()]
MELCOW_NEW_USERS = is_enabled((environ.get('MELCOW_NEW_USERS', "True")), True)
PROTECT_CONTENT = is_enabled((environ.get('PROTECT_CONTENT', "False")), False)
PUBLIC_FILE_STORE = is_enabled((environ.get('PUBLIC_FILE_STORE', "False")), False)
DELETE_TIME = int(environ.get('DELETE_TIME', 160))
START_IMAGE_URL = environ.get('START_IMAGE_URL', "https://graph.org/file/b7bfe0352ba19d3c0d21d.jpg")

#Session Name
SESSION_NAME = str(getenv('SESSION_NAME', 'prosearchfather'))

LOG_STR = "Current Cusomized Configurations are:-\n"
LOG_STR += ("IMDB Results are enabled, Bot will be showing imdb details for you queries.\n" if IMDB else "IMBD Results are disabled.\n")
LOG_STR += ("P_TTI_SHOW_OFF found , Users will be redirected to send /start to Bot PM instead of sending file file directly\n" if P_TTI_SHOW_OFF else "P_TTI_SHOW_OFF is disabled files will be send in PM, instead of sending start.\n")
LOG_STR += ("SINGLE_BUTTON is Found, filename and files size will be shown in a single button instead of two separate buttons\n" if SINGLE_BUTTON else "SINGLE_BUTTON is disabled , filename and file_sixe will be shown as different buttons\n")
LOG_STR += (f"CUSTOM_FILE_CAPTION enabled with value {CUSTOM_FILE_CAPTION}, your files will be send along with this customized caption.\n" if CUSTOM_FILE_CAPTION else "No CUSTOM_FILE_CAPTION Found, Default captions of file will be used.\n")
LOG_STR += ("Long IMDB storyline enabled." if LONG_IMDB_DESCRIPTION else "LONG_IMDB_DESCRIPTION is disabled , Plot will be shorter.\n")
LOG_STR += ("Spell Check Mode Is Enabled, bot will be suggesting related movies if movie not found\n" if SPELL_CHECK_REPLY else "SPELL_CHECK_REPLY Mode disabled\n")
LOG_STR += (f"MAX_LIST_ELM Found, long list will be shortened to first {MAX_LIST_ELM} elements\n" if MAX_LIST_ELM else "Full List of casts and crew will be shown in imdb template, restrict them by adding a value to MAX_LIST_ELM\n")
LOG_STR += f"Your current IMDB template is {IMDB_TEMPLATE}"
