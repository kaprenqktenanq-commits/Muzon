from pyrogram import filters

# List of preview/shortened URL patterns to block
BLOCKED_URL_PATTERNS = [
    't.me/c/',  # Telegram channel preview links
    'youtu.be/',  # YouTube shortened links
    'youtube.com/shorts/',  # YouTube shorts
    'bit.ly/',  # Bit.ly shortened URLs
    'tinyurl.com/',  # TinyURL
    'ow.ly/',  # Owl.ly shortened URLs
    'goo.gl/',  # Google shortened URLs
    'short.link/',  # Short.link
    'is.gd/',  # is.gd shortened URLs
    'buff.ly/',  # Buff.ly
    'adf.ly/',  # Adf.ly
    'clck.ru/',  # Clck.ru (Yandex)
    'lnk.co/',
    'rb.gy/',
    'lihi.io/',
    'snip.ly/',
]

def no_preview_urls(flt, client, message):
    """Filter to block messages containing preview or shortened URLs"""
    if not message:
        return True
    
    # Check message text
    if message.text:
        text = message.text.lower()
        for pattern in BLOCKED_URL_PATTERNS:
            if pattern.lower() in text:
                return False
    
    # Check message caption
    if message.caption:
        caption = message.caption.lower()
        for pattern in BLOCKED_URL_PATTERNS:
            if pattern.lower() in caption:
                return False
    
    return True

# Create a reusable filter
no_preview_filter = filters.create(no_preview_urls)
