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
        # Get song title and metadata
        try:
            ydl_opts_meta = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
                }
            }
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
        
        download_success = False
        
        # ===== ATTEMPT 1: Try yt-dlp with audio-only format =====
        logger.info(f'[Attempt 1] yt-dlp audio format for: {video_url}')
        await processing_msg.edit_text('🔄 Downloading song (Method 1)...')
        try:
            ydl_opts_audio = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.splitext(filepath)[0],
                'quiet': False,
                'no_warnings': False,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5'
                },
                'extractor_args': {'youtube': {'player_client': ['web', 'android', 'ios']}}
            }
            if YOUTUBE_PROXY:
                ydl_opts_audio['proxy'] = YOUTUBE_PROXY
            
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts_audio).download([video_url]))
            
            # Check if converted to mp3
            if os.path.exists(filepath):
                download_success = True
                logger.info(f'✓ yt-dlp audio succeeded for {safe_title}')
        except Exception as e:
            logger.debug(f'yt-dlp audio format failed: {e}')
        
        # ===== ATTEMPT 2: Try yt-dlp with best format =====
        if not download_success:
            logger.info(f'[Attempt 2] yt-dlp best format for: {video_url}')
            await processing_msg.edit_text('🔄 Downloading song (Method 2)...')
            try:
                ydl_opts_best = {
                    'format': 'best',
                    'outtmpl': os.path.splitext(filepath)[0],
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 30,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
                if YOUTUBE_PROXY:
                    ydl_opts_best['proxy'] = YOUTUBE_PROXY
                
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts_best).download([video_url]))
                
                if os.path.exists(filepath):
                    download_success = True
                    logger.info(f'✓ yt-dlp best format succeeded for {safe_title}')
            except Exception as e:
                logger.debug(f'yt-dlp best format failed: {e}')
        
        # ===== ATTEMPT 3: Try external MP3 extraction services =====
        if not download_success:
            logger.info(f'[Attempt 3] External MP3 services for: {video_url}')
            await processing_msg.edit_text('🔄 Fetching song from external sources...')
            result = await try_external_mp3_extraction(video_url, filepath)
            if result and os.path.exists(filepath):
                download_success = True
                logger.info(f'✓ External extraction succeeded for {safe_title}')
        
        # ===== ATTEMPT 4: Try YouTube API with yt-dlp format fallback =====
        if not download_success:
            logger.info(f'[Attempt 4] YouTube format 18 fallback for: {video_url}')
            await processing_msg.edit_text('🔄 Downloading song (Format 18)...')
            try:
                ydl_opts_fallback = {
                    'format': '18',
                    'outtmpl': os.path.splitext(filepath)[0],
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 30
                }
                if YOUTUBE_PROXY:
                    ydl_opts_fallback['proxy'] = YOUTUBE_PROXY
                
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts_fallback).download([video_url]))
                
                if os.path.exists(filepath):
                    download_success = True
                    logger.info(f'✓ Format 18 fallback succeeded for {safe_title}')
            except Exception as e:
                logger.debug(f'Format 18 fallback failed: {e}')
        
        if not download_success:
            await processing_msg.edit_text('❌ Failed to download the song. All methods exhausted. YouTube may require authentication.')
            logger.error(f'All download methods failed for {safe_title}')
            return
        
        thumb_path = None
        if thumbnail_url:
            thumb_filename = f'{safe_title}_thumb.jpg'
            thumb_path = await download_thumbnail(thumbnail_url, thumb_filename)
        
        # The file might be saved with an extension (.mp4, .m4a etc), normalize to .mp3
        os.makedirs('downloads', exist_ok=True)
        if not os.path.exists(filepath):
            # Try to find the file with different extensions
            for ext in ['.mp3', '.m4a', '.wav', '.webm', '.mp4']:
                alt_path = os.path.splitext(filepath)[0] + ext
                if os.path.exists(alt_path):
                    if ext != '.mp3':
                        try:
                            os.rename(alt_path, filepath)
                            logger.info(f'Renamed {alt_path} to {filepath}')
                        except Exception as e:
                            logger.warning(f'Could not rename {alt_path}: {e}')
                            filepath = alt_path
                    break
        
        if not os.path.exists(filepath):
            await processing_msg.edit_text('❌ Downloaded file not found. Try using /play instead.')
            logger.error(f'File not found after download: {filepath}')
            return
        
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
