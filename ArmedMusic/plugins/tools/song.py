import os
import re
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from pyrogram import filters
from pyrogram.types import Message
from ytSearch import VideosSearch
from ArmedMusic import app
from ArmedMusic.utils.decorators.urls import no_preview_filter
from ArmedMusic.utils.external_extractors import try_external_mp3_extraction
from config import BANNED_USERS, YOUTUBE_PROXY
from ArmedMusic import LOGGER
logger = LOGGER(__name__)

def is_youtube_url(url: str) -> bool:
    youtube_regex = '(https?://)?(www\\.)?(youtube|youtu|youtube-nocookie)\\.(com|be)/(watch\\?v=|embed/|v/|.+\\?v=)?([^&=%\\?]{11})'
    return bool(re.match(youtube_regex, url))

async def download_thumbnail(url: str, filename: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    os.makedirs('downloads', exist_ok=True)
                    filepath = f'downloads/{filename}'
                    with open(filepath, 'wb') as f:
                        f.write(data)
                    return filepath
    except Exception as e:
        logger.error(f'Thumbnail download failed: {e}')
    return None

@app.on_message(filters.command(['song']) & ~BANNED_USERS & no_preview_filter)
async def song_download(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text('Please provide a song name or YouTube URL.\n\nExample: `/song Believer` or `/song https://www.youtube.com/watch?v=7wtfhZwyrcc`', disable_web_page_preview=True)
    query = message.text.split(None, 1)[1].strip()
    if is_youtube_url(query):
        video_url = query
    else:
        search = VideosSearch(query, limit=1)
        try:
            results = await search.next()
            if not results['result']:
                return await message.reply_text('No results found for this song.')
            video = results['result'][0]
            video_url = video['link']
        except Exception as e:
            logger.error(f'Search failed: {e}')
            return await message.reply_text('Failed to search for the song.')
    processing_msg = await message.reply_text('🔄 Downloading song... Please wait.')
    try:
        # Get song title and metadata without downloading (minimal yt-dlp usage)
        try:
            ydl_opts_meta = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
            if YOUTUBE_PROXY:
                ydl_opts_meta['proxy'] = YOUTUBE_PROXY
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                info_meta = await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts_meta).extract_info(video_url, download=False))
            title = info_meta.get('title', 'Unknown')
            uploader = info_meta.get('uploader', 'Unknown Artist')
            duration = info_meta.get('duration', 0)
            thumbnail_url = info_meta.get('thumbnail', '')
        except Exception as meta_e:
            logger.warning(f'Could not extract metadata: {meta_e}')
            title = 'Unknown'
            uploader = 'Unknown'
            duration = 0
            thumbnail_url = ''
        
        safe_title = re.sub('[<>:"/\\\\|?*]', '', f'{title} - {uploader}')
        filepath = f'downloads/{safe_title}.mp3'
        
        # Use ONLY external MP3 extraction services (no yt-dlp direct downloads)
        logger.info(f'Using external MP3 extraction services for: {video_url}')
        await processing_msg.edit_text('🔄 Fetching song from external sources...')
        download_success = False
        
        result = await try_external_mp3_extraction(video_url, filepath)
        if result and os.path.exists(filepath):
            download_success = True
            logger.info(f'External extraction succeeded for {safe_title}')
        
        if not download_success:
            await processing_msg.edit_text('❌ Failed to download the song. YouTube requires authentication.')
            return
        
        thumb_path = None
        if thumbnail_url:
            thumb_filename = f'{safe_title}_thumb.jpg'
            thumb_path = await download_thumbnail(thumbnail_url, thumb_filename)
        await message.reply_audio(audio=filepath, caption='@ArmedMusicBot', title=title, performer=uploader, duration=duration, thumb=thumb_path)
        try:
            os.remove(filepath)
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
        except:
            pass
        await processing_msg.delete()
    except Exception as e:
        logger.error(f'Song download failed: {e}')
        await processing_msg.edit_text('❌ Failed to download the song.')
