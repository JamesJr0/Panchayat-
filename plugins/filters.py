import io
from pyrogram import filters, Client, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.filters_mdb import (
    add_filter,
    get_filters,
    delete_filter,
    count_filters
)
from database.connections_mdb import active_connection
from utils import get_file_id, parser, split_quotes
from info import ADMINS


@Client.on_message(filters.command(['del']) & filters.incoming & filters.user(ADMINS))
async def deletefilter(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply("You are anonymous admin. Use /connect {message.chat.id} in PM")

    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except Exception as e:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
        st.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        and str(userid) not in ADMINS
    ):
        return

    try:
        cmd, text = message.text.split(" ", 1)
    except ValueError:
        await message.reply_text(
            "<i>Mention the filter name which you want to delete!</i>\n\n"
            "<code>/del filtername</code>\n\n"
            "Use /viewfilters to view all available filters",
            quote=True
        )
        return

    query = text.strip().lower()

    await delete_filter(message, query, grp_id)


@Client.on_message(filters.command('delall') & filters.incoming)
async def delallconfirm(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")

    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except Exception as e:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if st.status in [enums.ChatMemberStatus.OWNER] or str(userid) in ADMINS:
        await message.reply_text(
            f"This will delete all filters from '{title}'.\nDo you want to continue??",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="YES", callback_data="delallconfirm")],
                [InlineKeyboardButton(text="CANCEL", callback_data="delallcancel")]
            ]),
            quote=True
        )
