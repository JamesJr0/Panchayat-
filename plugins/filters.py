from pyrogram import Client, filters, enums
from pyrogram.types import Message
from plugins.get_poster import get_poster  # Assuming this is your poster fetching function

# Function to handle filter creation
@Client.on_message(filters.command('filter') & filters.incoming)
async def give_filter(client, message):
    await auto_filter(client, message)

# Main Auto Filter Function
async def auto_filter(client, message):
    await advantage_spell_chok(message)

# Corrected advantage_spell_chok Function
async def advantage_spell_chok(msg):
    # Extracting movie request text
    if " " in msg.text:
        mv_rqst = msg.text.split(" ", 1)[1]  # Extract movie request text
    else:
        await msg.reply_text("❌ No valid movie request found. Please provide a proper query.")
        return

    try:
        reqst_gle = mv_rqst.replace(" ", "+")
        movies = await get_poster(reqst_gle, bulk=True)

        if not movies:
            await msg.reply_text("❌ No movies found for your request.")
            return

        # Display movie results
        movie_list = "\n".join(movies)
        await msg.reply_text(f"🎬 Movies Found:\n{movie_list}")

    except Exception as e:
        await msg.reply_text(f"❌ Error occurred: {str(e)}")

# Function to delete filters
@Client.on_message(filters.command('del') & filters.incoming)
async def delete_filter_handler(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply("❌ You are an anonymous admin. Use /connect in PM.")
    
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("❌ Make sure I'm present in your group!", quote=True)
                return
        else:
            await message.reply_text("❌ I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
        st.status != enums.ChatMemberStatus.ADMINISTRATOR
        and st.status != enums.ChatMemberStatus.OWNER
        and str(userid) not in ADMINS
    ):
        return

    try:
        cmd, text = message.text.split(" ", 1)
    except:
        await message.reply_text(
            "<i>Mention the filter name you want to delete!</i>\n\n"
            "<code>/del filtername</code>\n\n"
            "Use /viewfilters to view all available filters.",
            quote=True
        )
        return

    query = text.lower()

    await delete_filter(message, query, grp_id)

# Function to delete all filters
@Client.on_message(filters.command('delall') & filters.incoming)
async def delallconfirm(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"❌ You are an anonymous admin. Use /connect {message.chat.id} in PM.")
    
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("❌ Make sure I'm present in your group!", quote=True)
                return
        else:
            await message.reply_text("❌ I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if st.status == enums.ChatMemberStatus.OWNER or str(userid) in ADMINS:
        await message.reply_text(
            f"This will delete all filters from '{title}'.\nDo you want to continue?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text="YES", callback_data="delallconfirm")],
                [InlineKeyboardButton(text="CANCEL", callback_data="delallcancel")]
            ]),
            quote=True
        )
