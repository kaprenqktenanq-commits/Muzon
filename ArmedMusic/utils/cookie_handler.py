"""
YouTube Cookie Handler - Manages and validates YouTube authentication cookies
"""
import os
from ArmedMusic import LOGGER

logger = LOGGER(__name__)

COOKIES_FILE = 'cookies/youtube_cookies.txt'


def ensure_cookies_directory():
    """Creates the cookies directory if it doesn't exist"""
    os.makedirs('cookies', exist_ok=True)


def fix_cookies_format():
    """
    Fixes YouTube cookies format by removing leading dots from domain names.
    Netscape-format cookies exported from browsers often have domain names starting with a dot.
    yt-dlp requires these to be removed.
    """
    if not os.path.exists(COOKIES_FILE):
        return False
    
    try:
        with open(COOKIES_FILE, 'r') as f:
            lines = f.readlines()
        
        # Fix format - remove leading dots
        fixed_lines = []
        for line in lines:
            if line.startswith('.'):
                line = line[1:]
            fixed_lines.append(line)
        
        with open(COOKIES_FILE, 'w') as f:
            f.writelines(fixed_lines)
        
        logger.info(f'Fixed cookies format at {COOKIES_FILE}')
        return True
    except Exception as e:
        logger.error(f'Error fixing cookies format: {e}')
        return False


def validate_cookies():
    """
    Validates that cookies file exists and has valid content.
    Returns True if cookies are available and valid.
    """
    ensure_cookies_directory()
    
    if not os.path.exists(COOKIES_FILE):
        logger.warning(f'Cookies file not found at {COOKIES_FILE}')
        logger.warning('YouTube downloads may fail without authentication cookies')
        logger.warning('See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp')
        return False
    
    try:
        with open(COOKIES_FILE, 'r') as f:
            content = f.read().strip()
        
        if not content:
            logger.warning('Cookies file is empty')
            return False
        
        # Check if file has valid Netscape cookie format (has at least header or data)
        lines = content.split('\n')
        has_content = any(line.strip() and not line.strip().startswith('#') for line in lines)
        
        if not has_content:
            logger.warning('Cookies file appears to be empty (no valid cookie entries)')
            return False
        
        # Fix format if needed
        fix_cookies_format()
        
        logger.info('YouTube cookies validated successfully')
        return True
    except Exception as e:
        logger.error(f'Error validating cookies: {e}')
        return False


def get_cookies_file():
    """Returns the path to cookies file if it exists and is valid, otherwise None"""
    if validate_cookies():
        return COOKIES_FILE
    return None
