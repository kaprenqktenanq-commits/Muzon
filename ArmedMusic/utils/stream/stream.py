import os
from random import randint
from typing import Union
from pyrogram.types import InlineKeyboardMarkup
import config
from ArmedMusic import Carbon, YouTube, app, LOGGER
from ArmedMusic.core.call import Anony
from ArmedMusic.misc import db
from ArmedMusic.utils.database import add_active_video_chat, is_active_chat
from ArmedMusic.utils.exceptions import AssistantErr
from ArmedMusic.utils.inline import aq_markup, close_markup, stream_markup, stream_markup_telegram, telegram_download_cache
from ArmedMusic.utils.pastebin import AnonyBin
from ArmedMusic.utils.stream.queue import put_queue, put_queue_index
from ArmedMusic.utils.thumbnails import get_thumb
from ArmedMusic.utils.formatters import remove_emoji


async def _add_requester_message_link(run, chat_id, caption_template, info_link, title, duration_min, user_name, reply_markup=None):
    """Edit the just-sent message so the requester name links to the message itself."""
    try:
        logger = LOGGER(__name__)
        if not run:
            return
        # Build message link: prefer chat username, else use t.me/c/<chat_id_without_prefix>/<msgid>
        chat_username = getattr(getattr(run, 'chat', None), 'username', None)
        try:
            message_id = run.message_id
        except AttributeError:
            logger.warning("run object does not have message_id attribute")
            return
        if chat_username:
            message_link = f"https://t.me/{chat_username}/{message_id}"
        else:
            cid = str(chat_id)
            if cid.startswith('-100'):
                short = cid[4:]
            elif cid.startswith('-'):
                short = cid[1:]
            else:
                short = cid
            message_link = f"https://t.me/c/{short}/{message_id}"
        new_user = f"<a href='{message_link}'>{user_name}</a>"
        # Remove emoji from title for display
        display_title = remove_emoji(title)
        new_caption = caption_template.format(info_link, display_title, duration_min, new_user)
        # Try editing caption (media) first, fallback to edit text
        try:
            await run.edit_caption(new_caption, reply_markup=reply_markup)
        except Exception:
            try:
                await run.edit_text(new_caption, reply_markup=reply_markup)
            except Exception as e:
                logger.warning(f'Failed to update requester link in message: {e}')
    except Exception as e:
        LOGGER(__name__).warning(f'Error in _add_requester_message_link: {e}')

async def stream(_, mystic, user_id, result, chat_id, user_name, original_chat_id, video: Union[bool, str]=None, streamtype: Union[bool, str]=None, spotify: Union[bool, str]=None, forceplay: Union[bool, str]=None):
    if not result:
        return
    if forceplay:
        await Anony.force_stop_stream(chat_id)
    if streamtype == 'playlist':
        msg = f"{_['play_19']}\n\n"
        count = 0
        for search in result:
            if int(count) == config.PLAYLIST_FETCH_LIMIT:
                continue
            try:
                title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(search, False if spotify else True)
            except:
                continue
            if str(duration_min) == 'None':
                continue
            if duration_sec > config.DURATION_LIMIT:
                continue
            if await is_active_chat(chat_id):
                await put_queue(chat_id, original_chat_id, f'vid_{vidid}', title, duration_min, user_name, vidid, user_id, 'video' if video else 'audio')
                position = len(db.get(chat_id)) - 1
                count += 1
                msg += f'{count}. {remove_emoji(title)[:70]}\n'
                msg += f"{_['play_20']} {position}\n\n"
            else:
                if not forceplay:
                    db[chat_id] = []
                status = True if video else None
                try:
                    file_path, direct = await YouTube.download(vidid, mystic, video=status, videoid=True)
                except:
                    raise AssistantErr(_['play_14'])
                if file_path is None:
                    raise AssistantErr(_['play_14'])
                await Anony.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
                await put_queue(chat_id, original_chat_id, file_path if direct else f'vid_{vidid}', title, duration_min, user_name, vidid, user_id, 'video' if video else 'audio', forceplay=forceplay)
                img = await get_thumb(vidid, user_id)
                button = stream_markup(_, chat_id, videoid=vidid)
                try:
                    display_title = remove_emoji(title)
                    run = await app.send_photo(chat_id, photo=img, caption=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{vidid}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                    db[chat_id][0]['mystic'] = run
                    db[chat_id][0]['markup'] = 'stream'
                    # update requester name to link to this message
                    await _add_requester_message_link(run, chat_id, _['stream_1'], f'https://t.me/{app.username}?start=info_{vidid}', title, duration_min, user_name, InlineKeyboardMarkup(button))
                except Exception:
                    display_title = remove_emoji(title)
                    run = await app.send_message(chat_id, text=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{vidid}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                    db[chat_id][0]['mystic'] = run
                    db[chat_id][0]['markup'] = 'stream'
                    await _add_requester_message_link(run, chat_id, _['stream_1'], f'https://t.me/{app.username}?start=info_{vidid}', title, duration_min, user_name, InlineKeyboardMarkup(button))
        if count == 0:
            return
        else:
            link = await AnonyBin(msg)
            lines = msg.count('\n')
            if lines >= 17:
                car = os.linesep.join(msg.split(os.linesep)[:17])
            else:
                car = msg
            carbon = await Carbon.generate(car, randint(100, 10000000))
            upl = close_markup(_)
            return await app.send_photo(original_chat_id, photo=carbon, caption=_['play_21'].format(position, link), reply_markup=upl)
    elif streamtype == 'youtube':
        link = result['link']
        vidid = result['vidid']
        title = result['title'].title()
        duration_min = result['duration_min']
        thumbnail = result['thumb']
        status = True if video else None
        try:
            file_path, direct = await YouTube.download(vidid, mystic, videoid=True, video=status)
        except:
            raise AssistantErr(_['play_14'])
        if file_path is None:
            raise AssistantErr(_['play_14'])
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path if direct else f'vid_{vidid}', title, duration_min, user_name, vidid, user_id, 'video' if video else 'audio')
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(chat_id=original_chat_id, text=_['queue_4'].format(position, title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
        else:
            if not forceplay:
                db[chat_id] = []
            await Anony.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
            await put_queue(chat_id, original_chat_id, file_path if direct else f'vid_{vidid}', title, duration_min, user_name, vidid, user_id, 'video' if video else 'audio', forceplay=forceplay)
            img = await get_thumb(vidid, user_id)
            button = stream_markup(_, chat_id, videoid=vidid)
            display_title = remove_emoji(title)
            try:
                run = await app.send_photo(chat_id, photo=img, caption=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{vidid}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                db[chat_id][0]['markup'] = 'stream'
            except Exception:
                run = await app.send_message(chat_id, text=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{vidid}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                db[chat_id][0]['markup'] = 'stream'
    elif streamtype == 'soundcloud':
        file_path = result['filepath']
        title = result['title']
        duration_min = result['duration_min']
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, 'audio')
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(chat_id=original_chat_id, text=_['queue_4'].format(position, title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
        else:
            if not forceplay:
                db[chat_id] = []
            await Anony.join_call(chat_id, original_chat_id, file_path, video=None)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, 'audio', forceplay=forceplay)
            button = stream_markup(_, chat_id)
            display_title = remove_emoji(title)
            try:
                run = await app.send_photo(chat_id, photo=config.SOUNDCLOUD_IMG_URL, caption=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{streamtype}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                await _add_requester_message_link(run, chat_id, _['stream_1'], f'https://t.me/{app.username}?start=info_{streamtype}', title, duration_min, user_name, InlineKeyboardMarkup(button))
            except Exception:
                run = await app.send_message(chat_id, text=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{streamtype}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                await _add_requester_message_link(run, chat_id, _['stream_1'], f'https://t.me/{app.username}?start=info_{streamtype}', title, duration_min, user_name, InlineKeyboardMarkup(button))
            db[chat_id][0]['markup'] = 'tg'
    elif streamtype == 'telegram':
        file_path = result['path']
        link = result['link']
        title = result['title'].title()
        duration_min = result['dur']
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, 'file_id', user_id, 'video' if video else 'audio', link=link)
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(chat_id=original_chat_id, text=_['queue_4'].format(position, title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
        else:
            if not forceplay:
                db[chat_id] = []
            await Anony.join_call(chat_id, original_chat_id, file_path, video=status)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, 'file_id', user_id, 'video' if video else 'audio', forceplay=forceplay, link=link)
            if video:
                await add_active_video_chat(chat_id)
            # Save file info for download button
            telegram_download_cache[user_id] = {'file_path': file_path, 'file_name': title}
            # Store link in database for later retrieval
            db[chat_id][0]['link'] = link
            button = stream_markup_telegram(_, chat_id, user_id)
            display_title = remove_emoji(title)
            try:
                run = await app.send_photo(chat_id, photo=config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL, caption=_['stream_1'].format(link, display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                await _add_requester_message_link(run, chat_id, _['stream_1'], link, title, duration_min, user_name, InlineKeyboardMarkup(button))
            except Exception as e:
                run = await app.send_message(chat_id, text=_['stream_1'].format(link, display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                await _add_requester_message_link(run, chat_id, _['stream_1'], link, title, duration_min, user_name, InlineKeyboardMarkup(button))
            db[chat_id][0]['markup'] = 'tg'
    elif streamtype == 'live':
        link = result['link']
        vidid = result['vidid']
        title = result['title'].title()
        thumbnail = result['thumb']
        duration_min = 'Live Track'
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, f'live_{vidid}', title, duration_min, user_name, vidid, user_id, 'video' if video else 'audio')
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(chat_id=original_chat_id, text=_['queue_4'].format(position, title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
        else:
            if not forceplay:
                db[chat_id] = []
                text = (_['queue_4'].format(position, title, duration_min, user_name),)
            if n == 0:
                raise AssistantErr(_['str_3'])
            await Anony.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail if thumbnail else None)
            await put_queue(chat_id, original_chat_id, f'live_{vidid}', title, duration_min, user_name, vidid, user_id, 'video' if video else 'audio', forceplay=forceplay)
            img = await get_thumb(vidid, user_id)
            button = stream_markup(_, chat_id, videoid=vidid)
            display_title = remove_emoji(title)
            try:
                run = await app.send_photo(chat_id, photo=img, caption=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{vidid}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                await _add_requester_message_link(run, chat_id, _['stream_1'], f'https://t.me/{app.username}?start=info_{vidid}', title, duration_min, user_name, InlineKeyboardMarkup(button))
            except Exception:
                run = await app.send_message(chat_id, text=_['stream_1'].format(f'https://t.me/{app.username}?start=info_{vidid}', display_title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
                await _add_requester_message_link(run, chat_id, _['stream_1'], f'https://t.me/{app.username}?start=info_{vidid}', title, duration_min, user_name, InlineKeyboardMarkup(button))
            db[chat_id][0]['markup'] = 'tg'
    elif streamtype == 'index':
        link = result
        title = 'ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ'
        duration_min = '00:00'
        if await is_active_chat(chat_id):
            await put_queue_index(chat_id, original_chat_id, 'index_url', title, duration_min, user_name, link, 'video' if video else 'audio')
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await mystic.edit_text(text=_['queue_4'].format(position, title, duration_min, user_name), reply_markup=InlineKeyboardMarkup(button))
        else:
            if not forceplay:
                db[chat_id] = []
            await Anony.join_call(chat_id, original_chat_id, link, video=True if video else None)
            await put_queue_index(chat_id, original_chat_id, 'index_url', title, duration_min, user_name, link, 'video' if video else 'audio', forceplay=forceplay)
            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(chat_id, photo=config.STREAM_IMG_URL, caption=_['stream_2'].format(user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
            except Exception as e:
                run = await app.send_message(chat_id, text=_['stream_2'].format(user_name), reply_markup=InlineKeyboardMarkup(button))
                db[chat_id][0]['mystic'] = run
            db[chat_id][0]['markup'] = 'tg'
            await mystic.delete()
