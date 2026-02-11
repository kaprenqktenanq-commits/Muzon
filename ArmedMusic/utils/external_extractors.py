"""External MP3 extraction services fallback"""
import asyncio
import aiohttp
from typing import Optional
import logging

# Setup logger for external extractors
logger = logging.getLogger(__name__)

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
    
    failed_services = []
    
    for idx, service in enumerate(services, 1):
        try:
            service_name = service.get('name', 'unknown')
            logger.debug(f'[{idx}/{len(services)}] Trying {service_name}...')
            
            if service_name == 'cobalt.tools':
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
                            timeout=aiohttp.ClientTimeout(total=30),
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                        ) as resp:
                            if resp.status == 200:
                                try:
                                    data = await resp.json()
                                except:
                                    data = {}
                                
                                if 'url' in data and data['url']:
                                    mp3_url = data['url']
                                    try:
                                        async with session.get(mp3_url, timeout=aiohttp.ClientTimeout(total=60)) as download_resp:
                                            if download_resp.status == 200:
                                                content = await download_resp.read()
                                                if len(content) > 10000:
                                                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                                    with open(filepath, 'wb') as f:
                                                        f.write(content)
                                                    logger.info(f'✓ {service_name} succeeded ({len(content)} bytes)')
                                                    return filepath
                                    except Exception as dl_e:
                                        logger.debug(f'{service_name}: download error: {str(dl_e)[:50]}')
                except Exception as e:
                    logger.debug(f'{service_name}: {str(e)[:100]}')
            
            elif service_name in ['yt-dlp-api1', 'ympe.co']:
                try:
                    async with aiohttp.ClientSession() as session:
                        method = service.get('method', 'POST').upper()
                        url_param = service.get('url_param', 'url')
                        
                        if method == 'GET':
                            async with session.get(
                                service['api'],
                                params={url_param: video_url},
                                timeout=aiohttp.ClientTimeout(total=30),
                                headers={'User-Agent': 'Mozilla/5.0'}
                            ) as resp:
                                if resp.status == 200:
                                    try:
                                        data = await resp.json()
                                        mp3_url = data.get('link') or data.get('url') or data.get('downloadLink')
                                        if mp3_url:
                                            async with session.get(mp3_url, timeout=aiohttp.ClientTimeout(total=60)) as dl:
                                                if dl.status == 200:
                                                    content = await dl.read()
                                                    if len(content) > 10000:
                                                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                                        with open(filepath, 'wb') as f:
                                                            f.write(content)
                                                        logger.info(f'✓ {service_name} succeeded ({len(content)} bytes)')
                                                        return filepath
                                    except:
                                        pass
                except Exception as e:
                    logger.debug(f'{service_name}: {str(e)[:100]}')
            
            else:
                # Generic handler for other services
                try:
                    method = service.get('method', 'POST').upper()
                    url_param = service.get('url_param', 'url')
                    
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                            'Accept': '*/*',
                            'Referer': 'https://www.google.com/'
                        }
                        
                        if method == 'GET':
                            async with session.get(
                                service['api'],
                                params={url_param: video_url},
                                timeout=aiohttp.ClientTimeout(total=30),
                                headers=headers
                            ) as resp:
                                if resp.status == 200:
                                    # Try JSON first
                                    try:
                                        data = await resp.json()
                                        mp3_url = data.get('url') or data.get('downloadLink') or data.get('link') or data.get('download')
                                    except:
                                        # If not JSON, try text parsing
                                        mp3_url = None
                                    
                                    if mp3_url:
                                        async with session.get(mp3_url, timeout=aiohttp.ClientTimeout(total=60)) as dl:
                                            if dl.status == 200:
                                                content = await dl.read()
                                                if len(content) > 10000:
                                                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                                    with open(filepath, 'wb') as f:
                                                        f.write(content)
                                                    logger.info(f'✓ {service_name} succeeded ({len(content)} bytes)')
                                                    return filepath
                        
                        else:  # POST
                            async with session.post(
                                service['api'],
                                data={url_param: video_url},
                                timeout=aiohttp.ClientTimeout(total=30),
                                headers=headers
                            ) as resp:
                                if resp.status == 200:
                                    # Try JSON first
                                    try:
                                        data = await resp.json()
                                        mp3_url = data.get('url') or data.get('downloadLink') or data.get('link') or data.get('download')
                                    except:
                                        mp3_url = None
                                    
                                    if mp3_url:
                                        async with session.get(mp3_url, timeout=aiohttp.ClientTimeout(total=60)) as dl:
                                            if dl.status == 200:
                                                content = await dl.read()
                                                if len(content) > 10000:
                                                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                                    with open(filepath, 'wb') as f:
                                                        f.write(content)
                                                    logger.info(f'✓ {service_name} succeeded ({len(content)} bytes)')
                                                    return filepath
                except Exception as e:
                    logger.debug(f'{service_name}: {str(e)[:100]}')
        
        except Exception as service_error:
            logger.debug(f'{service.get("name", "unknown")}: {str(service_error)[:50]}')
    
    logger.warning(f'All {len(services)} external services failed')
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
