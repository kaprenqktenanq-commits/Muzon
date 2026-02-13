import os
import re
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
import subprocess
import json
from pyrogram import filters
from pyrogram.types import Message
import logging
from ArmedMusic import app
from ArmedMusic.utils.decorators.urls import no_preview_filter
from ArmedMusic.utils.external_extractors import try_external_mp3_extraction
from config import BANNED_USERS, YOUTUBE_PROXY
from ArmedMusic import LOGGER
logger = LOGGER(__name__)

def is_youtube_url(url: str) -> bool:
    youtube_regex = '(https?://)?(www\\.)?(youtube|youtu|youtube-nocookie)\\.(com|be)/(watch\\?v=|embed/|v/|.+\\?v=)?([^&=%\\?]{11})'
    return bool(re.match(youtube_regex, url))

async def search_youtube(query: str, limit: int = 1) -> list:
    """Search YouTube using yt-dlp instead of youtubesearchpython to avoid httpx compatibility issues"""
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            def _search():
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'default_search': 'ytsearch',
                    'extract_flat': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    results = ydl.extract_info(f'ytsearch{limit}:{query}', download=False)
                    return results.get('entries', [])
            
            results = await loop.run_in_executor(None, _search)
            return results
    except Exception as e:
        logger.error(f'YouTube search error: {type(e).__name__}: {e}')
        return []

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
        try:
            results = await search_youtube(query, limit=1)
            if not results:
                return await message.reply_text('No results found for this song.')
            video = results[0]
            video_url = f"https://www.youtube.com/watch?v={video['id']}"
        except Exception as e:
            logger.error(f'Search failed: {e}')
            return await message.reply_text('Failed to search for the song.')
    processing_msg = await message.reply_text('🔄 Downloading song... Please wait.')
    try:
        safe_title = re.sub('[<>:"/\\\\|?*]', '', 'Unknown - Unknown')
        filepath = f'downloads/{safe_title}.mp3'
        
        # ===== STEP 1: Get metadata and search for YouTube URL =====
        logger.info(f'Song request for: {query}')
        
        if not is_youtube_url(query):
            try:
                await processing_msg.edit_text('🔄 Searching for song...')
                results = await search_youtube(query, limit=1)
                if not results:
                    return await processing_msg.edit_text('❌ No results found for this song.')
                video = results[0]
                video_url = f"https://www.youtube.com/watch?v={video['id']}"
                title = video.get('title', 'Unknown')
                uploader = 'YouTube'
                duration = 0
                thumbnail_url = video.get('thumbnails', [{}])[0].get('url', '')
                logger.info(f'Found video: {title}')
            except Exception as e:
                logger.error(f'Search failed: {e}')
                return await processing_msg.edit_text('❌ Failed to search for the song.')
        else:
            video_url = query
            title = 'Unknown'
            uploader = 'YouTube'
            duration = 0
            thumbnail_url = ''
        
        # ===== STEP 2: Skip metadata extraction (causes YouTube auth errors) =====
        # We use default values to avoid triggering YouTube authentication requirements
        logger.debug(f'Skipping metadata extraction to avoid YouTube authentication errors')
        
        safe_title = re.sub('[<>:"/\\\\|?*]', '', f'{title} - {uploader}')
        filepath = f'downloads/{safe_title}.mp3'
        
        download_success = False
        
        # ===== ATTEMPT 1: Try yt-dlp with audio format (primary) =====
        logger.info(f'[Attempt 1] Trying yt-dlp bestaudio for: {video_url}')
        await processing_msg.edit_text('🔄 Converting audio with yt-dlp (Method 1)...')
        if not download_success:
            try:
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.splitext(filepath)[0],
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 20,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
                if YOUTUBE_PROXY:
                    ydl_opts['proxy'] = YOUTUBE_PROXY
                
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    await loop.run_in_executor(
                        executor,
                        lambda: yt_dlp.YoutubeDL(ydl_opts).download([video_url])
                    )
                
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    if file_size > 10000:
                        download_success = True
                        logger.info(f'✓ yt-dlp bestaudio succeeded ({file_size} bytes)')
            except Exception as e:
                logger.debug(f'yt-dlp bestaudio failed: {str(e)[:100]}')
        
        # ===== ATTEMPT 2: Simple direct download with yt-dlp =====
        if not download_success:
            logger.info(f'[Attempt 2] Trying yt-dlp direct best for: {video_url}')
            await processing_msg.edit_text('🔄 Converting audio with yt-dlp (Method 2)...')
            try:
                ydl_opts = {
                    'format': 'best',
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 20,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
                if YOUTUBE_PROXY:
                    ydl_opts['proxy'] = YOUTUBE_PROXY
                
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    await loop.run_in_executor(
                        executor,
                        lambda: yt_dlp.YoutubeDL(ydl_opts).download([video_url])
                    )
                
                # Look for any downloaded file and rename to mp3
                download_dir = 'downloads'
                if os.path.exists(download_dir):
                    for fname in os.listdir(download_dir):
                        if fname != f'{safe_title}.mp3':
                            potential_file = os.path.join(download_dir, fname)
                            try:
                                os.rename(potential_file, filepath)
                                logger.info(f'Renamed {fname} to {safe_title}.mp3')
                                break
                            except:
                                pass
                
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    if file_size > 10000:
                        download_success = True
                        logger.info(f'✓ yt-dlp best succeeded ({file_size} bytes)')
            except Exception as e:
                logger.debug(f'yt-dlp best failed: {str(e)[:100]}')
        
        # ===== ATTEMPT 3: Format 18 YouTube fallback =====
        if not download_success:
            logger.info(f'[Attempt 3] Trying format 18 for: {video_url}')
            await processing_msg.edit_text('🔄 Trying format 18...')
            try:
                ydl_opts = {
                    'format': '18',
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 20
                }
                if YOUTUBE_PROXY:
                    ydl_opts['proxy'] = YOUTUBE_PROXY
                
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    await loop.run_in_executor(
                        executor,
                        lambda: yt_dlp.YoutubeDL(ydl_opts).download([video_url])
                    )
                
                # Look for downloaded file
                for fname in os.listdir('downloads'):
                    potential_file = os.path.join('downloads', fname)
                    if os.path.getsize(potential_file) > 10000:
                        try:
                            os.rename(potential_file, filepath)
                            download_success = True
                            logger.info(f'✓ Format 18 succeeded')
                            break
                        except:
                            pass
            except Exception as e:
                logger.debug(f'Format 18 failed: {str(e)[:100]}')
        
        # ===== ATTEMPT 4: External MP3 services (fallback) =====
        if not download_success:
            logger.info(f'[Attempt 4] Trying external MP3 services for: {video_url}')
            await processing_msg.edit_text('🔄 Fetching from external sources...')
            try:
                result = await try_external_mp3_extraction(video_url, filepath)
                if result and os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    if file_size > 10000:
                        download_success = True
                        logger.info(f'✓ External service succeeded ({file_size} bytes)')
            except Exception as e:
                logger.debug(f'External extraction fallback failed: {type(e).__name__}: {e}')

        if not download_success:
            await processing_msg.edit_text('❌ Download failed. Song may require authentication or not available.')
            logger.error(f'All download attempts failed for: {title}')
            return
        
        # ===== Send the audio file =====
        thumb_path = None
        try:
            if thumbnail_url:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(thumbnail_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                thumb_dir = 'downloads'
                                os.makedirs(thumb_dir, exist_ok=True)
                                thumb_filename = f'{re.sub("[^a-zA-Z0-9]", "", safe_title)}_thumb.jpg'
                                thumb_path = os.path.join(thumb_dir, thumb_filename)
                                with open(thumb_path, 'wb') as f:
                                    f.write(await resp.read())
                except Exception as e:
                    logger.debug(f'Thumbnail download failed: {e}')
            
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                logger.info(f'Sending audio file: {filepath} ({file_size} bytes)')
                
                await message.reply_audio(
                    audio=filepath,
                    title=title,
                    performer=uploader,
                    duration=int(duration) if duration else 0,
                    thumb=thumb_path,
                    caption='@ArmedMusicBot'
                )
                
                await processing_msg.delete()
            else:
                await processing_msg.edit_text('❌ File not found after download.')
        
        except Exception as e:
            logger.error(f'Failed to send audio: {e}')
            await processing_msg.edit_text(f'❌ Failed to send audio file.')
        
        finally:
            # Cleanup
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.debug(f'Cleaned up: {filepath}')
            except:
                pass
            try:
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
                    logger.debug(f'Cleaned up: {thumb_path}')
            except:
                pass
    
    except Exception as e:
        logger.error(f'Song download error: {e}')
        try:
            await processing_msg.edit_text(f'❌ Error: {str(e)[:50]}')
        except:
            pass
