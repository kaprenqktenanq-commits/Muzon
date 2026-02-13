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
        'format_param': 'audio',
        'timeout': 30
    },
    {
        'name': 'yt-dlp-api1',
        'api': 'https://api.onlineconverter.com/api/v1/youtube-to-mp3',
        'method': 'GET',
        'url_param': 'url',
        'timeout': 30
    },
    {
        'name': 'ympe.co',
        'api': 'https://www.ympe.co/api/convert',
        'method': 'POST',
        'url_param': 'link',
        'timeout': 30
    },
    {
        'name': 'y2mate.com',
        'api': 'https://www.y2mate.com/api/info',
        'method': 'POST',
        'url_param': 'url',
        'timeout': 30
    },
    {
        'name': 'savefrom.net',
        'api': 'https://savefrom.net/api/info',
        'method': 'GET',
        'url_param': 'url',
        'timeout': 30
    },
]

async def try_external_mp3_extraction(video_url: str, filepath: str, timeout: int = 90) -> Optional[str]:
    """
    Try to download MP3 from external MP3 extraction services with timeout.
    Returns filepath on success, None on all failures.
    """
    import os
    import random
    
    try:
        # Randomize service order to distribute load
        services = EXTERNAL_SERVICES.copy()
        random.shuffle(services)
        
        for idx, service in enumerate(services, 1):
            if asyncio.get_event_loop().time() + 30 > asyncio.get_event_loop().time() + timeout:
                logger.warning("External extraction timeout reached")
                break
                
            service_name = service.get('name', 'unknown')
            service_timeout = aiohttp.ClientTimeout(total=service.get('timeout', 30))
            
            try:
                method = service.get('method', 'POST').upper()
                url_param = service.get('url_param', 'url')
                
                async with aiohttp.ClientSession(timeout=service_timeout) as session:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                        'Accept': '*/*',
                    }
                    
                    try:
                        if method == 'GET':
                            async with session.get(
                                service['api'],
                                params={url_param: video_url},
                                headers=headers
                            ) as resp:
                                if resp.status == 200:
                                    try:
                                        data = await resp.json()
                                    except:
                                        data = {}
                                    
                                    mp3_url = data.get('url') or data.get('downloadLink') or data.get('link')
                                    if mp3_url:
                                        try:
                                            async with session.get(mp3_url, timeout=service_timeout) as dl:
                                                if dl.status == 200:
                                                    content = await dl.read()
                                                    if len(content) > 50000:  # Minimum 50KB
                                                        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
                                                        with open(filepath, 'wb') as f:
                                                            f.write(content)
                                                        logger.info(f'✓ {service_name} succeeded ({len(content)//1024}KB)')
                                                        return filepath
                                        except asyncio.TimeoutError:
                                            logger.debug(f'{service_name}: download timeout')
                                        except Exception as dl_e:
                                            logger.debug(f'{service_name}: download failed')
                        else:  # POST
                            async with session.post(
                                service['api'],
                                data={url_param: video_url},
                                headers=headers
                            ) as resp:
                                if resp.status == 200:
                                    try:
                                        data = await resp.json()
                                        mp3_url = data.get('url') or data.get('downloadLink') or data.get('link')
                                    except:
                                        mp3_url = None
                                    
                                    if mp3_url:
                                        try:
                                            async with session.get(mp3_url, timeout=service_timeout) as dl:
                                                if dl.status == 200:
                                                    content = await dl.read()
                                                    if len(content) > 50000:
                                                        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
                                                        with open(filepath, 'wb') as f:
                                                            f.write(content)
                                                        logger.info(f'✓ {service_name} succeeded ({len(content)//1024}KB)')
                                                        return filepath
                                        except asyncio.TimeoutError:
                                            logger.debug(f'{service_name}: download timeout')
                                        except Exception as dl_e:
                                            logger.debug(f'{service_name}: download failed')
                    except asyncio.TimeoutError:
                        logger.debug(f'{service_name}: API call timeout')
                    except Exception as e:
                        logger.debug(f'{service_name}: API error')
                        
            except asyncio.TimeoutError:
                logger.debug(f'{service_name}: session timeout')
            except Exception as service_error:
                logger.debug(f'{service_name}: connection error')
            
            # Small delay between services
            await asyncio.sleep(0.5)
        
        logger.warning(f'All external services exhausted ({len(services)} tried)')
        return None
        
    except Exception as outer_e:
        logger.error(f"External extraction fatal error: {type(outer_e).__name__}")
        return None
    import subprocess
    
    # Randomize service order to distribute load
    services = EXTERNAL_SERVICES.copy()
    import random
    random.shuffle(services)


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
                logger.warning(f"Retry failed after {max_retries} attempts")
                raise
            # Exponential backoff: 2s, 4s, 8s
            delay = base_delay ** (attempt + 1)
            logger.debug(f"Retry backoff: waiting {delay}s before attempt {attempt + 2}/{max_retries}")
            await asyncio.sleep(delay)
    return None
