import asyncio
import glob
import json
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Union
import string
import requests
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ytSearch import VideosSearch, CustomSearch
import base64
import subprocess
from ArmedMusic import LOGGER
from ArmedMusic.utils.database import is_on_off
from ArmedMusic.utils.formatters import time_to_seconds
from ArmedMusic.utils.external_extractors import try_external_mp3_extraction, retry_with_backoff
ITALIC_TO_REGULAR = str.maketrans({119860: 'A', 119861: 'B', 119862: 'C', 119863: 'D', 119864: 'E', 119865: 'F', 119866: 'G', 119867: 'H', 119868: 'I', 119869: 'J', 119870: 'K', 119871: 'L', 119872: 'M', 119873: 'N', 119874: 'O', 119875: 'P', 119876: 'Q', 119877: 'R', 119878: 'S', 119879: 'T', 119880: 'U', 119881: 'V', 119882: 'W', 119883: 'X', 119884: 'Y', 119885: 'Z', 119886: 'a', 119887: 'b', 119888: 'c', 119889: 'd', 119890: 'e', 119891: 'f', 119892: 'g', 119893: 'h', 119894: 'i', 119895: 'j', 119896: 'k', 119897: 'l', 119898: 'm', 119899: 'n', 119900: 'o', 119901: 'p', 119902: 'q', 119903: 'r', 119904: 's', 119905: 't', 119906: 'u', 119907: 'v', 119908: 'w', 119909: 'x', 119910: 'y', 119911: 'z', 120328: 'A', 120329: 'B', 120330: 'C', 120331: 'D', 120332: 'E', 120333: 'F', 120334: 'G', 120335: 'H', 120336: 'I', 120337: 'J', 120338: 'K', 120339: 'L', 120340: 'M', 120341: 'N', 120342: 'O', 120343: 'P', 120344: 'Q', 120345: 'R', 120346: 'S', 120347: 'T', 120348: 'U', 120349: 'V', 120350: 'W', 120351: 'X', 120352: 'Y', 120353: 'Z', 120354: 'a', 120355: 'b', 120356: 'c', 120357: 'd', 120358: 'e', 120359: 'f', 120360: 'g', 120361: 'h', 120362: 'i', 120363: 'j', 120364: 'k', 120365: 'l', 120366: 'm', 120367: 'n', 120368: 'o', 120369: 'p', 120370: 'q', 120371: 'r', 120372: 's', 120373: 't', 120374: 'u', 120375: 'v', 120376: 'w', 120377: 'x', 120378: 'y', 120379: 'z', 120380: 'A', 120381: 'B', 120382: 'C', 120383: 'D', 120384: 'E', 120385: 'F', 120386: 'G', 120387: 'H', 120388: 'I', 120389: 'J', 120390: 'K', 120391: 'L', 120392: 'M', 120393: 'N', 120394: 'O', 120395: 'P', 120396: 'Q', 120397: 'R', 120398: 'S', 120399: 'T', 120400: 'U', 120401: 'V', 120402: 'W', 120403: 'X', 120404: 'Y', 120405: 'Z', 120406: 'a', 120407: 'b', 120408: 'c', 120409: 'd', 120410: 'e', 120411: 'f', 120412: 'g', 120413: 'h', 120414: 'i', 120415: 'j', 120416: 'k', 120417: 'l', 120418: 'm', 120419: 'n', 120420: 'o', 120421: 'p', 120422: 'q', 120423: 'r', 120424: 's', 120425: 't', 120426: 'u', 120427: 'v', 120428: 'w', 120429: 'x', 120430: 'y', 120431: 'z'})

def convert_italic_unicode(text):
    return text.translate(ITALIC_TO_REGULAR)

from config import YT_API_KEY, YTPROXY_URL as YTPROXY, YOUTUBE_PROXY, YOUTUBE_USE_PYTUBE, YOUTUBE_INVIDIOUS_INSTANCES, YOUTUBE_FALLBACK_SEARCH_LIMIT

logger = LOGGER(__name__)

async def check_file_size(link):

    async def get_format_info(link):
        cmd = ['yt-dlp', '--js-runtimes', 'node', '-J', link]
        if YOUTUBE_PROXY:
            cmd.extend(['--proxy', YOUTUBE_PROXY])
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE) 
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f'Error:\n{stderr.decode()}')
            return None
        return json.loads(stdout.decode())

    def parse_size(formats):
        total_size = 0
        for format in formats:
            if 'filesize' in format:
                total_size += format['filesize']
        return total_size
    info = await get_format_info(link)
    if info is None:
        return None
    formats = info.get('formats', [])
    if not formats:
        print('No formats found.')
        return None
    total_size = parse_size(formats)
    return total_size

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, errorz = await proc.communicate()
    if errorz:
        if 'unavailable videos are hidden' in errorz.decode('utf-8').lower():
            return out.decode('utf-8')
        else:
            return errorz.decode('utf-8')
    return out.decode('utf-8')

class YouTubeAPI:

    def __init__(self):
        self.base = 'https://www.youtube.com/watch?v='
        self.regex = '(?:youtube\\.com|youtu\\.be)'
        self.status = 'https://www.youtube.com/oembed?url='
        self.listbase = 'https://youtube.com/playlist?list='
        self.reg = re.compile('\\x1B(?:[@-Z\\\\-_]|\\[[0-?]*[ -/]*[@-~])')
        self.dl_stats = {'total_requests': 0, 'okflix_downloads': 0, 'existing_files': 0}
        self.invidious_index = 0
        self.fallback_search_limit = YOUTUBE_FALLBACK_SEARCH_LIMIT

    def _next_invidious(self):
        if not YOUTUBE_INVIDIOUS_INSTANCES:
            return None
        inst = YOUTUBE_INVIDIOUS_INSTANCES[self.invidious_index % len(YOUTUBE_INVIDIOUS_INSTANCES)]
        self.invidious_index = (self.invidious_index + 1) % len(YOUTUBE_INVIDIOUS_INSTANCES)
        return inst
    async def exists(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ''
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = (entity.offset, entity.length)
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset:offset + length]

    async def details(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())['result']:
            title = result['title']
            title = convert_italic_unicode(title)
            duration_min = result['duration']
            thumbnail = result['thumbnails'][0]['url'].split('?')[0]
            vidid = result['id']
            if str(duration_min) == 'None':
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return (title, duration_min, duration_sec, thumbnail, vidid)

    async def title(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())['result']:
            title = result['title']
            title = convert_italic_unicode(title)
        return title

    async def duration(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())['result']:
            duration = result['duration']
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())['result']:
            thumbnail = result['thumbnails'][0]['url'].split('?')[0]
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        
        # Dynamically build format candidates from extractor info, prefer audio-only
        url_to_check = f'https://www.youtube.com/watch?v={vid_id}'
        format_options = []
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl_info:
                info_local = ydl_info.extract_info(url_to_check, download=False)
                formats = info_local.get('formats', []) or []
                audio_only = [f for f in formats if f.get('acodec') and f.get('acodec') != 'none' and (not f.get('vcodec') or f.get('vcodec') == 'none')]
                if audio_only:
                    audio_sorted = sorted(audio_only, key=lambda f: float(f.get('abr') or 0), reverse=True)
                    format_options.extend([f.get('format_id') for f in audio_sorted if f.get('format_id')])
                video_fmts = [f for f in formats if f.get('vcodec') and f.get('vcodec') != 'none']
                if video_fmts:
                    video_sorted = sorted(video_fmts, key=lambda f: int(f.get('height') or 0), reverse=True)
                    format_options.extend([f.get('format_id') for f in video_sorted if f.get('format_id')])
        except Exception as info_e:
            logger.debug(f'Could not extract formats for dynamic selection: {info_e}')

        # Deduplicate while preserving order and add safe fallbacks
        seen = set()
        deduped = []
        for f in format_options:
            if f and f not in seen:
                deduped.append(f)
                seen.add(f)
        deduped.extend(["bestaudio/best", "best", "18"])  # fallbacks

        for fmt in deduped:
            try:
                cmd = ['yt-dlp', '-g', '-f', fmt, f'{link}']
                if YOUTUBE_PROXY:
                    cmd.extend(['--proxy', YOUTUBE_PROXY])
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await proc.communicate()
                if stdout:
                    url = stdout.decode().split('\n')[0]
                    if url:
                        return (1, url)
            except Exception as fmt_e:
                logger.warning(f'Format {fmt} failed for video URL: {str(fmt_e)}')
                continue
        
        return (0, "All format options failed")

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str]=None):
        if videoid:
            link = self.listbase + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        playlist = await shell_cmd(f'yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}')
        try:
            result = playlist.split('\n')
            for key in result:
                if key == '':
                    result.remove(key)
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        results = VideosSearch(link, limit=1)
        res = await results.next()
        results_list = res['result']
        if not results_list:
            raise ValueError("ꜰᴀɪʟᴇᴅ ᴛᴏ ꜰᴇᴛᴄʜ ᴛʀᴀᴄᴋ ᴅᴇᴛᴀɪʟs. ᴛʀʏ ᴘʟᴀʏɪɴɢ ᴀɴʏ ᴏᴛʜᴇʀ.")
        for result in results_list:
            title = result['title']
            duration_min = result['duration']
            vidid = result['id']
            yturl = result['link']
            thumbnail = result['thumbnails'][0]['url'].split('?')[0]
        track_details = {'title': title, 'link': yturl, 'vidid': vidid, 'duration_min': duration_min, 'thumb': thumbnail}
        return (track_details, vidid)

    async def formats(self, link: str, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        ytdl_opts = {'quiet': True, 'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language': 'en-us,en;q=0.5', 'Sec-Fetch-Mode': 'navigate'}, 'js_runtimes': {'node': {}}, 'skip_unavailable_fragments': True, 'retries': 3, 'fragment_retries': 3}
        info_opts = {
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language': 'en-us,en;q=0.5', 'Sec-Fetch-Mode': 'navigate'},
            'js_runtimes': {'node': {}},
            'socket_timeout': 30
        }
        ydl_info = yt_dlp.YoutubeDL(info_opts)
        with ydl_info:
            formats_available = []
            r = ydl_info.extract_info(link, download=False)
            for format in r['formats']:
                try:
                    str(format['format'])
                except:
                    continue
                if not 'dash' in str(format['format']).lower():
                    try:
                        format['format']
                        format['filesize']
                        format['format_id']
                        format['ext']
                        format['format_note']
                    except:
                        continue
                    formats_available.append({'format': format['format'], 'filesize': format['filesize'], 'format_id': format['format_id'], 'ext': format['ext'], 'format_note': format['format_note'], 'yturl': link})
        return (formats_available, link)

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str]=None):
        if videoid:
            link = self.base + link
        if '&' in link:
            link = link.split('&')[0]
        if '?si=' in link:
            link = link.split('?si=')[0]
        elif '&si=' in link:
            link = link.split('&si=')[0]
        try:
            results = []
            search = VideosSearch(link, limit=10)
            search_results = (await search.next()).get('result', [])
            for result in search_results:
                duration_str = result.get('duration', '0:00')
                try:
                    parts = duration_str.split(':')
                    duration_secs = 0
                    if len(parts) == 3:
                        duration_secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    elif len(parts) == 2:
                        duration_secs = int(parts[0]) * 60 + int(parts[1])
                    if duration_secs <= 3600:
                        results.append(result)
                except (ValueError, IndexError):
                    continue
            if not results or query_type >= len(results):
                raise ValueError('No suitable videos found within duration limit')
            selected = results[query_type]
            return (selected['title'], selected['duration'], selected['thumbnails'][0]['url'].split('?')[0], selected['id'])
        except Exception as e:
            LOGGER(__name__).error(f'Error in slider: {str(e)}')
            raise ValueError('Failed to fetch video details')

    async def download(self, link: str, mystic, video: Union[bool, str]=None, videoid: Union[bool, str]=None, songaudio: Union[bool, str]=None, songvideo: Union[bool, str]=None, format_id: Union[bool, str]=None, title: Union[bool, str]=None) -> str:
        if videoid:
            vid_id = link
            link = self.base + link
        loop = asyncio.get_running_loop()

        def create_session():
            session = requests.Session()
            retries = Retry(total=10, backoff_factor=0.1)
            session.mount('http://', HTTPAdapter(max_retries=retries))
            session.mount('https://', HTTPAdapter(max_retries=retries))
            return session

        async def download_with_requests(url, filepath, headers=None):
            try:
                session = create_session()
                response = session.get(url, headers=headers, stream=True, timeout=60, allow_redirects=True)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 1024 * 1024
                with open(filepath, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                return filepath
            except Exception as e:
                logger.error(f'Requests download failed: {str(e)}')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return None
            finally:
                session.close()

        async def audio_dl(vid_id):
            try:
                filepath = os.path.join('downloads', f'{vid_id}.mp3')
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                if os.path.exists(filepath):
                    return filepath
                # Safely attempt to get video info; ensure `info` is always defined
                info = None
                requires_auth = False
                # Pre-check: detect if video requires authentication
                try:
                    check_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'socket_timeout': 15,
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                        },
                        'extractor_args': {'youtube': {'player_client': ['web']}}
                    }
                    with yt_dlp.YoutubeDL(check_opts) as ydl_check:
                        ydl_check.extract_info(f'https://www.youtube.com/watch?v={vid_id}', download=False)
                except Exception as check_e:
                    error_msg = str(check_e)
                    if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                        logger.warning(f'Video {vid_id} requires authentication - skipping YouTube attempts, using fallbacks only')
                        requires_auth = True
                    info = None
                try:
                    info_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'js_runtimes': {'node': {}},
                        'socket_timeout': 30,
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web'], 'player_skip': ['js', 'webpage'], 'innertube_client': 'ios'}}
                    }
                    with yt_dlp.YoutubeDL(info_opts) as ydl:
                        info = ydl.extract_info(f'https://www.youtube.com/watch?v={vid_id}', download=False)
                        formats = info.get('formats', [])
                        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                        logger.info(f'Available pure audio formats for {vid_id}: {len(audio_formats)} formats')
                        if audio_formats:
                            logger.info(f'First pure audio format: {audio_formats[0]}')
                        else:
                            audio_formats = [f for f in formats if f.get('acodec') != 'none']
                            logger.info(f'Available audio+video formats for {vid_id}: {len(audio_formats)} formats')
                            if audio_formats:
                                logger.info(f'First audio+video format: {audio_formats[0]}')
                except Exception as info_e:
                    logger.warning(f'Failed to get info for {vid_id}: {str(info_e)}')
                # Try invidious instances first
                if YOUTUBE_INVIDIOUS_INSTANCES:
                    for _ in range(len(YOUTUBE_INVIDIOUS_INSTANCES)):
                        inst = self._next_invidious()
                        if not inst:
                            break
                        try:
                            invid_url = f"{inst.rstrip('/')}/watch?v={vid_id}"
                            ydl_fallback = {'format': 'bestaudio/best', 'outtmpl': os.path.join('downloads', f'{vid_id}'), 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}], 'quiet': True, 'no_warnings': True, 'retries': 5, 'fragment_retries': 5, 'skip_unavailable_fragments': True, 'js_runtimes': {'node': {}}}
                            if YOUTUBE_PROXY:
                                ydl_fallback['proxy'] = YOUTUBE_PROXY
                            loop = asyncio.get_running_loop()
                            with ThreadPoolExecutor() as executor:
                                await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_fallback).download([invid_url]))
                            if os.path.exists(filepath):
                                logger.info(f'Invidious download succeeded with {inst}')
                                return filepath
                        except Exception as e:
                            error_msg = str(e)
                            # Skip if authentication-related or network-related
                            if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                                logger.warning(f'Invidious {inst} requires authentication (skipping)')
                            elif 'Failed to resolve' in error_msg or 'Name or service not known' in error_msg:
                                logger.warning(f'Invidious {inst} DNS/network error (skipping)')
                            else:
                                logger.warning(f'Invidious {inst} failed for {vid_id}: {e}')
                # Try pytube if enabled
                if YOUTUBE_USE_PYTUBE:
                    try:
                        from pytube import YouTube as PyTube
                        tmpfile = os.path.join('downloads', f'{vid_id}_pytube')
                        yt_obj = PyTube(f'https://www.youtube.com/watch?v={vid_id}')
                        stream = yt_obj.streams.filter(only_audio=True).order_by('abr').desc().first()
                        if stream:
                            out = stream.download(output_path='downloads', filename=f'{vid_id}_pytube')
                            # convert to mp3
                            mp3path = filepath
                            try:
                                subprocess.run(['ffmpeg', '-y', '-i', out, '-vn', '-ab', '192k', mp3path], check=True)
                                if os.path.exists(mp3path):
                                    logger.info('pytube download succeeded and converted to mp3')
                                    # cleanup original
                                    if os.path.exists(out) and out != mp3path:
                                        os.remove(out)
                                    return mp3path
                            except Exception as conv_e:
                                logger.warning(f'ffmpeg conversion failed for {out}: {conv_e}')
                    except Exception as py_e:
                        error_msg = str(py_e)
                        # Skip if authentication-related
                        if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                            logger.warning(f'pytube requires authentication (skipping): {error_msg}')
                        else:
                            logger.warning(f'pytube failed for {vid_id}: {py_e}')
                ydl_opts_list = [
                    {
                        'format': 'bestaudio/best',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 5,
                        'fragment_retries': 5,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        'extractor_args': {'youtube': {'player_client': ['web'], 'player_skip': ['js'], 'innertube_client': 'web'}}
                    },
                    {
                        'format': 'bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/140/bestaudio/best[ext=mp4]/best',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 5,
                        'fragment_retries': 5,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        'extractor_args': {'youtube': {'player_client': ['ios'], 'player_skip': ['js'], 'innertube_client': 'ios'}}
                    },
                    {
                        'format': 'bestaudio',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 3,
                        'fragment_retries': 3,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1',
                            'DNT': '1',
                            'Sec-Fetch-User': '?1',
                            'Sec-Ch-Ua-Mobile': '?1',
                            'Sec-Ch-Ua-Platform': '"Android"'
                        },
                        'extractor_args': {'youtube': {'player_client': ['android'], 'player_skip': ['js'], 'innertube_client': 'android'}}
                    },
                    {
                        'format': '140/171/251/bestaudio[ext=m4a]/bestaudio',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 3,
                        'fragment_retries': 3,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/133.0',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept-Encoding': 'gzip, deflate, br',
                            'DNT': '1',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1'
                        }
                    },
                    {
                        'format': 'bestaudio',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 3,
                        'fragment_retries': 3,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}}
                    },
                    {
                        'format': 'bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/140/bestaudio/best[ext=mp4]/best',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 5,
                        'fragment_retries': 5,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'com.google.android.youtube/19.09.36 (Linux; U; Android 11; SM-G973F) gzip',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5'
                        },
                        'extractor_args': {'youtube': {'player_client': ['android_music'], 'player_skip': ['js'], 'innertube_client': 'android_music'}}
                    },
                    {
                        'format': 'bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/140/bestaudio/best[ext=mp4]/best',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 5,
                        'fragment_retries': 5,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        'extractor_args': {'youtube': {'player_client': ['web_embedded'], 'player_skip': ['js'], 'innertube_client': 'web_embedded'}}
                    },
                    {
                        'format': 'bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/140/bestaudio/best[ext=mp4]/best',
                        'outtmpl': os.path.join('downloads', f'{vid_id}'),
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 5,
                        'fragment_retries': 5,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        'extractor_args': {'youtube': {'player_client': ['web_safari'], 'player_skip': ['js'], 'innertube_client': 'web_safari'}}
                    }
                ]
                # Skip direct YouTube yt-dlp download attempts if video requires authentication
                if not requires_auth:
                    for i in range(len(ydl_opts_list)):
                        try:
                            logger.info(f'Trying download configuration {i + 1} for {vid_id}')
                            ydl_opts = ydl_opts_list[i].copy()
                            if YOUTUBE_PROXY and 'proxy' not in ydl_opts:
                                ydl_opts['proxy'] = YOUTUBE_PROXY
                            loop = asyncio.get_running_loop()
                            with ThreadPoolExecutor() as executor:
                                result = await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts).download([f'https://www.youtube.com/watch?v={vid_id}']))
                                logger.info(f'yt_dlp download result for {vid_id} (config {i + 1}): {result}')
                            logger.info(f'Checking for file at {filepath}')
                            if os.path.exists(filepath):
                                logger.info(f'File found: {filepath}')
                                return filepath
                            else:
                                logger.warning(f'Download config {i + 1} completed but file not found at {filepath}')
                        except Exception as e:
                            error_msg = str(e)
                            # Skip this variant if it requires authentication
                            if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                                logger.warning(f'Download config {i + 1} requires authentication (skipping): {error_msg}')
                                continue
                            logger.warning(f'Download config {i + 1} failed for {vid_id}: {error_msg}')
                            continue
                    logger.error(f'All download configurations failed for {vid_id}')
                else:
                    logger.info(f'Skipping all direct YouTube yt-dlp methods for {vid_id} (requires authentication)')
                # Fallback: try direct stream URLs via yt-dlp -g then download via requests
                try:
                    cmd = ['yt-dlp', '--format', 'bestaudio/best', '--js-runtimes', 'node', '-g', f'https://www.youtube.com/watch?v={vid_id}']
                    if YOUTUBE_PROXY:
                        cmd.extend(['--proxy', YOUTUBE_PROXY])
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    stdout, stderr = await proc.communicate()
                    stderr_str = stderr.decode()
                    # Check if error is authentication-related
                    if 'Sign in to confirm' in stderr_str or 'cookies' in stderr_str.lower():
                        logger.warning(f'Direct stream fallback requires authentication (skipping)')
                    elif proc.returncode == 0 and stdout:
                        urls = stdout.decode().splitlines()
                        for u in urls:
                            res = await download_with_requests(u, filepath)
                            if res:
                                logger.info('Direct stream fallback succeeded')
                                return res
                except Exception as ds_e:
                    logger.warning(f'Direct-stream fallback failed: {ds_e}')
                # Additional fallback: try legacy `youtube_dl` library if available
                try:
                    import youtube_dl as legacy_ytdl
                    try:
                        legacy_opts = {
                            'format': 'bestaudio/best',
                            'outtmpl': os.path.join('downloads', f'{vid_id}'),
                            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                            'quiet': True,
                            'no_warnings': True,
                        }
                        with legacy_ytdl.YoutubeDL(legacy_opts) as ydl_l:
                            ydl_l.download([f'https://www.youtube.com/watch?v={vid_id}'])
                        if os.path.exists(filepath):
                            logger.info('Legacy youtube_dl fallback succeeded')
                            return filepath
                    except Exception as ly_e:
                        error_msg = str(ly_e)
                        # Skip if authentication-related
                        if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                            logger.warning(f'Legacy youtube_dl requires authentication (skipping): {error_msg}')
                        else:
                            logger.warning(f'Legacy youtube_dl fallback failed: {ly_e}')
                except Exception:
                    # youtube_dl not installed or import failed - ignore
                    pass
                # Fallback: External MP3 extraction services (cloud converters)
                try:
                    logger.info(f'Trying external MP3 extraction services for {vid_id}')
                    ext_result = await try_external_mp3_extraction(f'https://www.youtube.com/watch?v={vid_id}', filepath)
                    if ext_result and os.path.exists(filepath):
                        logger.info('External MP3 extraction service succeeded')
                        return filepath
                except Exception as ext_e:
                    error_msg = str(ext_e)
                    # Skip if authentication-related
                    if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                        logger.warning(f'External services require authentication (skipping): {error_msg}')
                    else:
                        logger.warning(f'External MP3 extraction failed: {ext_e}')
                # Fallback: search for other videos with the same title and try them
                try:
                    if info and isinstance(info, dict) and info.get('title'):
                        title = info.get('title')
                        search = VideosSearch(title, limit=self.fallback_search_limit)
                        results = (await search.next()).get('result', [])
                        for r in results:
                            alt_vid = r.get('id')
                            if alt_vid and alt_vid != vid_id:
                                logger.info(f'Trying alternative video {alt_vid} for title match')
                                alt_res = await audio_dl(alt_vid)
                                if alt_res:
                                    return alt_res
                except Exception as s_e:
                    error_msg = str(s_e)
                    # Skip if authentication-related
                    if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                        logger.warning(f'Fallback search requires authentication (skipping)')
                    else:
                        logger.warning(f'Fallback search failed: {s_e}')
                return None
            except Exception as e:
                logger.error(f'yt_dlp audio download failed for {vid_id}: {str(e)}')
                return None

        async def video_dl(vid_id):
            try:
                filepath = os.path.join('downloads', f'{vid_id}.mp4')
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                if os.path.exists(filepath):
                    return filepath
                
                # Pre-check: detect if video requires authentication
                try:
                    check_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'socket_timeout': 15,
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                        },
                        'extractor_args': {'youtube': {'player_client': ['web']}}
                    }
                    with yt_dlp.YoutubeDL(check_opts) as ydl_check:
                        ydl_check.extract_info(f'https://www.youtube.com/watch?v={vid_id}', download=False)
                except Exception as check_e:
                    error_msg = str(check_e)
                    if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                        logger.warning(f'Video {vid_id} requires authentication - skipping YouTube attempt for video, using fallbacks only')
                        # Return None to skip all yt-dlp attempts
                        return None
                
                # Dynamically build format candidates from extractor info for this vid
                url_to_check = f'https://www.youtube.com/watch?v={vid_id}'
                format_options = []
                try:
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl_info:
                        info_local = ydl_info.extract_info(url_to_check, download=False)
                        formats = info_local.get('formats', []) or []
                        audio_only = [f for f in formats if f.get('acodec') and f.get('acodec') != 'none' and (not f.get('vcodec') or f.get('vcodec') == 'none')]
                        if audio_only:
                            audio_sorted = sorted(audio_only, key=lambda f: float(f.get('abr') or 0), reverse=True)
                            format_options.extend([f.get('format_id') for f in audio_sorted if f.get('format_id')])
                        video_fmts = [f for f in formats if f.get('vcodec') and f.get('vcodec') != 'none']
                        if video_fmts:
                            video_sorted = sorted(video_fmts, key=lambda f: int(f.get('height') or 0), reverse=True)
                            format_options.extend([f.get('format_id') for f in video_sorted if f.get('format_id')])
                except Exception as info_e:
                    logger.debug(f'Could not extract formats for dynamic selection: {info_e}')

                seen = set()
                deduped = []
                for f in format_options:
                    if f and f not in seen:
                        deduped.append(f)
                        seen.add(f)
                deduped.extend(["bestaudio/best", "best", "18/best"])  # fallbacks

                for fmt in deduped:
                    try:
                        ydl_opts = {
                            'format': fmt,
                            'outtmpl': filepath,
                            'quiet': True,
                            'no_warnings': True,
                            'retries': 10,
                            'fragment_retries': 10,
                            'skip_unavailable_fragments': True, 
                            'http_headers': {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 
                                'Accept-Language': 'en-us,en;q=0.5', 
                                'Sec-Fetch-Mode': 'navigate', 
                                'Sec-Fetch-Dest': 'document', 
                                'Sec-Fetch-Site': 'none', 
                                'Sec-Fetch-User': '?1', 
                                'Upgrade-Insecure-Requests': '1'
                            }, 
                            'extractor_args': {
                                'youtube': {
                                    'player_client': ['web'], 
                                    'player_skip': ['js'], 
                                    'innertube_client': 'web'
                                }
                            }
                        }
                        if YOUTUBE_PROXY:
                            ydl_opts['proxy'] = YOUTUBE_PROXY
                        loop = asyncio.get_running_loop()
                        with ThreadPoolExecutor() as executor:
                            await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts).download([f'https://www.youtube.com/watch?v={vid_id}']))
                        if os.path.exists(filepath):
                            logger.info(f'Video download succeeded with format: {fmt}')
                            return filepath
                    except Exception as fmt_e:
                        error_msg = str(fmt_e)
                        # Skip this variant if it requires authentication
                        if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                            logger.warning(f'Format {fmt} requires authentication (skipping): {error_msg}')
                        else:
                            logger.warning(f'Format {fmt} failed for {vid_id}: {error_msg}')
                        # Remove partial file if it exists
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        continue
                
                logger.error('All video format options failed')
                return None
            except Exception as e:
                logger.error(f'yt_dlp video download failed for {vid_id}: {str(e)}')
                return None

        async def song_video_dl():
            try:
                filepath = f'downloads/{title}.mp4'
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                if os.path.exists(filepath):
                    return filepath
                
                # Dynamically build format candidates from extractor info for this vid
                url_to_check = f'https://www.youtube.com/watch?v={vid_id}'
                format_options = []
                try:
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl_info:
                        info_local = ydl_info.extract_info(url_to_check, download=False)
                        formats = info_local.get('formats', []) or []
                        audio_only = [f for f in formats if f.get('acodec') and f.get('acodec') != 'none' and (not f.get('vcodec') or f.get('vcodec') == 'none')]
                        if audio_only:
                            audio_sorted = sorted(audio_only, key=lambda f: float(f.get('abr') or 0), reverse=True)
                            format_options.extend([f.get('format_id') for f in audio_sorted if f.get('format_id')])
                        video_fmts = [f for f in formats if f.get('vcodec') and f.get('vcodec') != 'none']
                        if video_fmts:
                            video_sorted = sorted(video_fmts, key=lambda f: int(f.get('height') or 0), reverse=True)
                            format_options.extend([f.get('format_id') for f in video_sorted if f.get('format_id')])
                except Exception as info_e:
                    logger.debug(f'Could not extract formats for dynamic selection: {info_e}')

                seen = set()
                deduped = []
                for f in format_options:
                    if f and f not in seen:
                        deduped.append(f)
                        seen.add(f)
                deduped.extend(["bestaudio/best", "best", "18/best"])  # fallbacks

                for fmt in deduped:
                    try:
                        ydl_opts = {
                            'format': fmt,
                            'outtmpl': filepath,
                            'quiet': True,
                            'no_warnings': True,
                            'retries': 10,
                            'fragment_retries': 10,
                            'skip_unavailable_fragments': True,
                            'http_headers': {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                'Accept-Language': 'en-us,en;q=0.5',
                                'Sec-Fetch-Mode': 'navigate',
                                'Sec-Fetch-Dest': 'document',
                                'Sec-Fetch-Site': 'none',
                                'Sec-Fetch-User': '?1',
                                'Upgrade-Insecure-Requests': '1'
                            },
                            'extractor_args': {
                                'youtube': {
                                    'player_client': ['web'],
                                    'player_skip': ['js'],
                                    'innertube_client': 'web'
                                }
                            }
                        }
                        if YOUTUBE_PROXY:
                            ydl_opts['proxy'] = YOUTUBE_PROXY
                        loop = asyncio.get_running_loop()
                        with ThreadPoolExecutor() as executor:
                            await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url_to_check]))
                        if os.path.exists(filepath):
                            logger.info(f'Song video download succeeded with format: {fmt}')
                            return filepath
                    except Exception as fmt_e:
                        error_msg = str(fmt_e)
                        # Skip this variant if it requires authentication
                        if 'Sign in to confirm' in error_msg or 'cookies' in error_msg.lower():
                            logger.warning(f'Format {fmt} requires authentication (skipping): {error_msg}')
                        else:
                            logger.warning(f'Format {fmt} failed for song video {vid_id}: {error_msg}')
                        # Remove partial file if it exists
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        continue
                
                logger.error('All song video format options failed')
                return None
            except Exception as e:
                logger.error(f'yt_dlp song video download failed for {vid_id}: {str(e)}')
                return None

        async def song_audio_dl():
            try:
                filepath = f'downloads/{title}.mp3'
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                if os.path.exists(filepath):
                    return filepath
                # Try invidious instances first
                if YOUTUBE_INVIDIOUS_INSTANCES:
                    for _ in range(len(YOUTUBE_INVIDIOUS_INSTANCES)):
                        inst = self._next_invidious()
                        if not inst:
                            break
                        try:
                            invid_url = f"{inst.rstrip('/')}/watch?v={vid_id}"
                            ydl_fallback = {'format': 'bestaudio/best', 'outtmpl': f'downloads/{title}', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}], 'quiet': True, 'no_warnings': True, 'retries': 5, 'fragment_retries': 5, 'skip_unavailable_fragments': True, 'js_runtimes': {'node': {}}}
                            if YOUTUBE_PROXY:
                                ydl_fallback['proxy'] = YOUTUBE_PROXY
                            loop = asyncio.get_running_loop()
                            with ThreadPoolExecutor() as executor:
                                await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_fallback).download([invid_url]))
                            if os.path.exists(filepath):
                                logger.info(f'Invidious song download succeeded with {inst}')
                                return filepath
                        except Exception as e:
                            logger.warning(f'Invidious {inst} failed for song {vid_id}: {e}')
                # Try pytube if enabled
                if YOUTUBE_USE_PYTUBE:
                    try:
                        from pytube import YouTube as PyTube
                        yt_obj = PyTube(f'https://www.youtube.com/watch?v={vid_id}')
                        stream = yt_obj.streams.filter(only_audio=True).order_by('abr').desc().first()
                        if stream:
                            out = stream.download(output_path='downloads', filename=f'{title}_pytube')
                            # convert to mp3
                            mp3path = filepath
                            try:
                                subprocess.run(['ffmpeg', '-y', '-i', out, '-vn', '-ab', '192k', mp3path], check=True)
                                if os.path.exists(mp3path):
                                    logger.info('pytube song download succeeded and converted to mp3')
                                    # cleanup original
                                    if os.path.exists(out) and out != mp3path:
                                        os.remove(out)
                                    return mp3path
                            except Exception as conv_e:
                                logger.warning(f'ffmpeg conversion failed for song {out}: {conv_e}')
                    except Exception as py_e:
                        logger.warning(f'pytube failed for song {vid_id}: {py_e}')
                ydl_opts_list = [
                    {
                        'format': 'bestaudio/best',
                        'outtmpl': f'downloads/{title}',
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 5,
                        'fragment_retries': 5,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        'extractor_args': {'youtube': {'player_client': ['web'], 'player_skip': ['js'], 'innertube_client': 'web'}}
                    },
                    {
                        'format': 'bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/140/bestaudio/best[ext=mp4]/best',
                        'outtmpl': f'downloads/{title}',
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 5,
                        'fragment_retries': 5,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        'extractor_args': {'youtube': {'player_client': ['ios'], 'player_skip': ['js'], 'innertube_client': 'ios'}}
                    },
                    {
                        'format': 'bestaudio',
                        'outtmpl': f'downloads/{title}',
                        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}],
                        'quiet': True,
                        'no_warnings': True,
                        'retries': 3,
                        'fragment_retries': 3,
                        'skip_unavailable_fragments': True,
                        'js_runtimes': {'node': {}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-us,en;q=0.5',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1',
                            'DNT': '1',
                            'Sec-Fetch-User': '?1',
                            'Sec-Ch-Ua-Mobile': '?1',
                            'Sec-Ch-Ua-Platform': '"Android"'
                        },
                        'extractor_args': {'youtube': {'player_client': ['android'], 'player_skip': ['js'], 'innertube_client': 'android'}}
                    }
                ]
                for i, ydl_opts in enumerate(ydl_opts_list):
                    try:
                        logger.info(f'Trying song audio download configuration {i + 1} for {vid_id}')
                        if YOUTUBE_PROXY and 'proxy' not in ydl_opts:
                            ydl_opts['proxy'] = YOUTUBE_PROXY
                        loop = asyncio.get_running_loop()
                        with ThreadPoolExecutor() as executor:
                            await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_opts).download([f'https://www.youtube.com/watch?v={vid_id}']))
                        if os.path.exists(filepath):
                            return filepath
                        else:
                            logger.warning(f'Song audio download config {i + 1} completed but file not found at {filepath}')
                    except Exception as e:
                        error_msg = str(e)
                        logger.warning(f'Song audio download config {i + 1} failed for {vid_id}: {error_msg}')
                        if 'page needs to be reloaded' not in error_msg and 'Requested format is not available' not in error_msg:
                            break
                        continue
                logger.error(f'All song audio download configurations failed for {vid_id}')
                # Fallback: Invidious instances (rotated)
                if YOUTUBE_INVIDIOUS_INSTANCES:
                    for _ in range(len(YOUTUBE_INVIDIOUS_INSTANCES)):
                        inst = self._next_invidious()
                        if not inst:
                            break
                        try:
                            invid_url = f"{inst.rstrip('/')}/watch?v={vid_id}"
                            ydl_fallback = {'format': 'bestaudio/best', 'outtmpl': f'downloads/{title}', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}], 'quiet': True, 'no_warnings': True}
                            if YOUTUBE_PROXY:
                                ydl_fallback['proxy'] = YOUTUBE_PROXY
                            loop = asyncio.get_running_loop()
                            with ThreadPoolExecutor() as executor:
                                await loop.run_in_executor(executor, lambda: yt_dlp.YoutubeDL(ydl_fallback).download([invid_url]))
                            if os.path.exists(filepath):
                                logger.info(f'Invidious fallback succeeded with {inst}')
                                return filepath
                        except Exception as e:
                            logger.warning(f'Invidious fallback {inst} failed for {vid_id}: {e}')
                # Fallback: pytube
                if YOUTUBE_USE_PYTUBE:
                    try:
                        from pytube import YouTube as PyTube
                        stream = PyTube(f'https://www.youtube.com/watch?v={vid_id}').streams.filter(only_audio=True).order_by('abr').desc().first()
                        if stream:
                            out = stream.download(output_path='downloads', filename=f'{title}_pytube')
                            mp3path = filepath
                            try:
                                subprocess.run(['ffmpeg', '-y', '-i', out, '-vn', '-ab', '192k', mp3path], check=True)
                                if os.path.exists(mp3path):
                                    if os.path.exists(out) and out != mp3path:
                                        os.remove(out)
                                    return mp3path
                            except Exception as conv_e:
                                logger.warning(f'ffmpeg conversion failed for {out}: {conv_e}')
                    except Exception as py_e:
                        logger.warning(f'pytube fallback failed for {vid_id}: {py_e}')
                # Fallback: try direct stream URLs via yt-dlp -g then download via requests
                try:
                    cmd = ['yt-dlp', '--format', 'bestaudio/best', '--js-runtimes', 'node', '-g', f'https://www.youtube.com/watch?v={vid_id}']
                    if YOUTUBE_PROXY:
                        cmd.extend(['--proxy', YOUTUBE_PROXY])
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    stdout, stderr = await proc.communicate()
                    if proc.returncode == 0 and stdout:
                        urls = stdout.decode().splitlines()
                        for u in urls:
                            res = await download_with_requests(u, filepath)
                            if res:
                                logger.info('Direct stream fallback succeeded')
                                return res
                except Exception as ds_e:
                    logger.warning(f'Direct-stream fallback failed: {ds_e}')
                # Fallback: search for other videos with the same title and try them
                try:
                    if title:
                        search = VideosSearch(title, limit=self.fallback_search_limit)
                        results = (await search.next()).get('result', [])
                        for r in results:
                            alt_vid = r.get('id')
                            if alt_vid and alt_vid != vid_id:
                                logger.info(f'Trying alternative video {alt_vid} for title match')
                                alt_res = await song_audio_dl(alt_vid)
                                if alt_res:
                                    return alt_res
                except Exception as s_e:
                    logger.warning(f'Fallback search failed: {s_e}')
                return None
            except Exception as e:
                logger.error(f'yt_dlp song audio download failed for {vid_id}: {str(e)}')
                return None
        if songvideo:
            fpath = await song_video_dl()
            return fpath
        elif songaudio:
            fpath = await song_audio_dl()
            return fpath
        elif video:
            direct = True
            downloaded_file = await video_dl(vid_id)
        else:
            direct = True
            downloaded_file = await audio_dl(vid_id)
        return (downloaded_file, direct)
