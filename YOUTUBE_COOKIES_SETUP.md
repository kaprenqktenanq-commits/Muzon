# YouTube Cookies Setup Guide

## Problem
The bot fails to download songs from YouTube with the error:
```
ERROR: [youtube] ...: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.
```

This happens because YouTube requires authentication to bypass age-restricted or bot-detection measures.

## Solution: Adding YouTube Cookies

### Method 1: Using a Browser Extension (Recommended)

1. **Install a Cookie Exporter Extension**
   - For Chrome/Chromium: Install "Get cookies.txt" or "Cookie-Editor"
   - For Firefox: Install "cookies.txt" add-on

2. **Export Cookies**
   - Visit https://www.youtube.com
   - Make sure you're logged into your YouTube account
   - Click the extension icon and export cookies
   - This creates a file in Netscape HTTP Cookie File format

3. **Add to Bot**
   - Create a `cookies` folder in your bot's root directory if it doesn't exist
   - Place the exported cookies file at `cookies/youtube_cookies.txt`
   - The bot will automatically detect and use it

### Method 2: Manual Setup with yt-dlp

```bash
# Extract cookies from your browser using yt-dlp
yt-dlp --cookies-from-browser chrome --cookies cookies/youtube_cookies.txt "https://www.youtube.com"

# Or for Firefox:
yt-dlp --cookies-from-browser firefox --cookies cookies/youtube_cookies.txt "https://www.youtube.com"
```

### Method 3: Using a Logged-in Session

If you have cookies from a logged-in browser session, they should work. Make sure to:
1. Be logged into YouTube in the browser from which you export cookies
2. Ensure the cookies include authentication tokens (usually has `YSC`, `PREF`, `CONSENT` cookies)
3. Include all cookie entries, not just a few

## Cookie File Format

The cookies should be in **Netscape HTTP Cookie File** format:

```
#HttpOnly_  .youtube.com	TRUE	/	TRUE	1735689600	PREF	...
#HttpOnly_	.youtube.com	TRUE	/	TRUE	1735689600	YSC	...
.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	...
```

**Important:** If your exported cookies start with a dot (`.`) in the domain name, the bot will automatically fix this on startup.

## Verification

After adding cookies:

1. **Check logs** - The bot will log: `YouTube cookies validated successfully`
2. **Try downloading** - Use `/song` command to test
3. **If it still fails:**
   - Ensure cookies.txt is in `cookies/youtube_cookies.txt`
   - Try re-exporting with fresh cookies
   - Check that your YouTube account is in good standing (no suspensions)

## Troubleshooting

### "Cookies file not found"
- Create the `cookies` directory in the bot's root folder
- Place your `youtube_cookies.txt` file in it

### "Cookies file is empty"
- Re-export your cookies from your browser
- Ensure you're logged into YouTube before exporting

### "Still getting authentication errors"
- Your cookies may have expired, try exporting fresh ones
- Make sure the browser you're exporting from has an active YouTube session
- Some browsers store cookies differently - try a different browser

### "Sign in to confirm you're not a bot"
- This usually means the cookies don't have proper authentication tokens
- Try logging out and in again on YouTube in your browser
- Then re-export the cookies

## Security Notes

⚠️ **Important:** Cookie files contain authentication tokens. Handle them securely:

- **Never** commit cookies.txt to version control
- **Never** share your cookies file with others (it's like sharing your password!)
- Keep cookies.txt private with appropriate file permissions
- Consider using a separate test account for bot cookies
- Re-generate cookies periodically for security

## Automatic Fixes

The bot automatically:
1. ✅ Creates the `cookies` directory if needed
2. ✅ Validates cookie file format
3. ✅ Fixes domain name formatting (removes leading dots)
4. ✅ Logs warnings if cookies are invalid or missing

## File Permissions

Make sure the cookies file is readable by the bot process:

```bash
chmod 600 cookies/youtube_cookies.txt
```

This ensures only the bot can read the sensitive cookie data.

## More Information

For more details, see:
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [yt-dlp Cookie Extraction Guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
