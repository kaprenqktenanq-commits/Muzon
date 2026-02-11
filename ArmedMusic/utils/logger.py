from pyrogram.enums import ParseMode
from ArmedMusic import app
from config import LOGGER_ID
from ArmedMusic.utils.formatters import clean_query

async def play_logs(message, streamtype):
    query = clean_query(message.text.split(None, 1)[1]) if len(message.text.split(None, 1)) > 1 else 'N/A'
    logger_text = f'\n<b>{app.mention} ᴘʟᴀʏ ʟᴏɢ</b>\n\n<b>ᴄʜᴀᴛ ɪᴅ :</b> <code>{message.chat.id}</code>\n<b>ᴄʜᴀᴛ ɴᴀᴍᴇ :</b> {message.chat.title}\n<b>ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.chat.username}\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ɴᴀᴍᴇ :</b> {message.from_user.mention}\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}\n\n<b>ǫᴜᴇʀʏ :</b> {query}\n<b>sᴛʀᴇᴀᴍᴛʏᴘᴇ :</b> {streamtype}'
    if message.chat.id != LOGGER_ID:
        try:
            await app.send_message(chat_id=LOGGER_ID, text=logger_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except:
            pass
    return
