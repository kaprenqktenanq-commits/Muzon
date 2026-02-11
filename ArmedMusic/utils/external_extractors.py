"""External MP3 extraction services fallback"""
import asyncio
import aiohttp
from typing import Optional

# External MP3 extraction services that work as cloud converters
EXTERNAL_SERVICES = [
    {
        'name': 'cobalt.tools',
        'api': 'https://api.cobalt.tools/api/json',
        'extractor': 'youtube',
        'format_param': 'audio'
    },
    {
        'name': 'yt-dlp-api1',
        'api': 'https://api.onlineconverter.com/api/v1/youtube-to-mp3',
        'method': 'GET',
        'url_param': 'url'
    },
    {
        'name': 'ympe.co',
        'api': 'https://www.ympe.co/api/convert',
        'method': 'POST',
        'url_param': 'link'
    },
    {
        'name': 'ytmp3.cc',
        'api': 'https://yt-downloader.org/api/button/mp3',
        'method': 'POST',
        'url_param': 'url'
    },
    {
        'name': 'y2mate.com',
        'api': 'https://www.y2mate.com/api/info',
        'method': 'POST',
        'url_param': 'url'
    },
    {
        'name': 'mp3youtube.download',
        'api': 'https://mp3youtube.download/api/download',
        'method': 'POST',
        'url_param': 'url'
    },
    {
        'name': 'tube2mp3.com',
        'api': 'https://api.tube2mp3.com/convert',
        'method': 'POST',
        'url_param': 'url'
    },
    {
        'name': 'savefrom.net',
        'api': 'https://savefrom.net/api/info',
        'method': 'GET',
        'url_param': 'url'
    },
    {
        'name': 'mp3juices.cc',
        'api': 'https://mp3juices.cc/api/convert',
        'method': 'POST',
        'url_param': 'url'
    },
    {
        'name': 'getmp3.cc',
        'api': 'https://getmp3.cc/api/convert',
        'method': 'POST',
        'url_param': 'url'
    },
]

async def try_external_mp3_extraction(video_url: str, filepath: str) -> Optional[str]:
    """
    Try to download MP3 from external MP3 extraction services.
    These are cloud-based converters that can bypass YouTube restrictions.
    Returns filepath on success, None on all failures.
    """
    import os
    import subprocess
    
    # Randomize service order to distribute load
    services = EXTERNAL_SERVICES.copy()
    import random
    random.shuffle(services)
    
    for service in services:
        try:
            service_name = service.get('name', 'unknown')
            
            if service_name == 'cobalt.tools':
                # Try cobalt.tools API
                try:
                    async with aiohttp.ClientSession() as session:
                        payload = {
                            'url': video_url,
                            'vimeoDash': False,
                            'audioDash': False,
                            'disableMetadata': False
                        }
                        async with session.post(
                            service['api'],
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if 'url' in data:
                                    # Download the file
                                    async with session.get(data['url']) as download_resp:
                                        if download_resp.status == 200:
                                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                            with open(filepath, 'wb') as f:
                                                f.write(await download_resp.read())
                                            return filepath
                except Exception as e:
                    continue
            
            elif service_name == 'yt-dlp-api1':
                # Try online converter API
                try:
                    async with aiohttp.ClientSession() as session:
                        params = {'url': video_url}
                        async with session.get(
                            service['api'],
                            params=params,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if 'link' in data or 'url' in data:
                                    mp3_url = data.get('link') or data.get('url')
                                    async with session.get(mp3_url) as download_resp:
                                        if download_resp.status == 200:
                                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                            with open(filepath, 'wb') as f:
                                                f.write(await download_resp.read())
                                            return filepath
                except Exception as e:
                    continue
            
            elif service_name == 'ympe.co':
                # Try YMPE API
                try:
                    async with aiohttp.ClientSession() as session:
                        payload = {'link': video_url}
                        async with session.post(
                            service['api'],
                            data=payload,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if 'url' in data or 'downloadLink' in data:
                                    mp3_url = data.get('url') or data.get('downloadLink')
                                    async with session.get(mp3_url) as download_resp:
                                        if download_resp.status == 200:
                                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                            with open(filepath, 'wb') as f:
                                                f.write(await download_resp.read())
                                            return filepath
                except Exception as e:
                    continue
            
            else:
                # Generic handler for other services
                try:
                    method = service.get('method', 'POST').upper()
                    url_param = service.get('url_param', 'url')
                    
                    async with aiohttp.ClientSession() as session:
                        if method == 'GET':
                            params = {url_param: video_url}
                            async with session.get(
                                service['api'],
                                params=params,
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    # Try common response keys
                                    mp3_url = data.get('url') or data.get('downloadLink') or data.get('link') or data.get('download')
                                    if mp3_url:
                                        async with session.get(mp3_url) as download_resp:
                                            if download_resp.status == 200:
                                                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                                with open(filepath, 'wb') as f:
                                                    f.write(await download_resp.read())
                                                return filepath
                        else:  # POST
                            payload = {url_param: video_url}
                            async with session.post(
                                service['api'],
                                json=payload,
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    mp3_url = data.get('url') or data.get('downloadLink') or data.get('link') or data.get('download')
                                    if mp3_url:
                                        async with session.get(mp3_url) as download_resp:
                                            if download_resp.status == 200:
                                                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                                with open(filepath, 'wb') as f:
                                                    f.write(await download_resp.read())
                                                return filepath
                except Exception as e:
                    continue
        
        except Exception as service_error:
            continue
    
    return None


async def retry_with_backoff(func, max_retries=3, base_delay=2):
    """
    Retry a coroutine function with exponential backoff.
    Useful for handling temporary YouTube anti-bot blocks.
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff: 2s, 4s, 8s
            delay = base_delay ** (attempt + 1)
            await asyncio.sleep(delay)
    return None
