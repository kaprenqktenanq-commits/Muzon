"""
YouTube search utility using yt-dlp instead of youtubesearchpython
to avoid httpx compatibility issues
"""
import asyncio
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
from ArmedMusic.logging import LOGGER

logger = LOGGER(__name__)


class VideosSearch:
    """Drop-in replacement for youtubesearchpython.VideosSearch using yt-dlp"""
    
    def __init__(self, query: str, limit: int = 1):
        self.query = query
        self.limit = limit
        self._results = None
    
    async def next(self):
        """Search and return results in youtubesearchpython format"""
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
                        results = ydl.extract_info(f'ytsearch{self.limit}:{self.query}', download=False)
                        return results.get('entries', [])
                
                entries = await loop.run_in_executor(None, _search)
            
            # Convert yt-dlp format to youtubesearchpython format for compatibility
            formatted_results = []
            for entry in entries:
                formatted_result = {
                    'id': entry.get('id', ''),
                    'title': entry.get('title', 'Unknown'),
                    'link': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    'channel': {
                        'name': entry.get('uploader', 'Unknown'),
                        'link': entry.get('channel_url', '')
                    },
                    'duration': self._format_duration(entry.get('duration', 0)),
                    'thumbnails': [{'url': entry.get('thumbnail', '')}] if entry.get('thumbnail') else [],
                    'viewCount': {'short': entry.get('view_count', 0)},
                    'publishedTime': entry.get('upload_date', 'Unknown'),
                }
                formatted_results.append(formatted_result)
            
            self._results = formatted_results
            return {'result': formatted_results}
        
        except Exception as e:
            logger.error(f'YouTube search error: {type(e).__name__}: {e}')
            return {'result': []}
    
    @staticmethod
    def _format_duration(seconds):
        """Convert seconds to MM:SS format"""
        if not seconds:
            return '0:00'
        seconds = int(seconds)
        mins = seconds // 60
        secs = seconds % 60
        return f'{mins}:{secs:02d}'


class CustomSearch(VideosSearch):
    """Compatibility class for youtubesearchpython.CustomSearch"""
    pass
