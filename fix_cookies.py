import os

def fix_cookies():
    """
    Fixes YouTube cookies format by removing leading dots from Netscape-format cookies.
    This is necessary when exporting cookies from browsers in the standard Netscape format.
    """
    cookies_path = 'cookies/youtube_cookies.txt'
    
    # Create cookies directory if it doesn't exist
    os.makedirs('cookies', exist_ok=True)
    
    # Check if cookies file exists
    if not os.path.exists(cookies_path):
        print(f"Cookies file not found at {cookies_path}")
        print("Please add your YouTube cookies to this file.")
        print("See https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp for instructions.")
        return False
    
    try:
        # Read the cookies file
        with open(cookies_path, 'r') as f:
            lines = f.readlines()
        
        # Fix the format - remove leading dots from domain names
        fixed_lines = []
        for line in lines:
            if line.startswith('.'):
                line = line[1:]
            fixed_lines.append(line)
        
        # Write back the fixed cookies
        with open(cookies_path, 'w') as f:
            f.writelines(fixed_lines)
        
        print(f"Successfully fixed cookies format at {cookies_path}")
        return True
    except Exception as e:
        print(f"Error fixing cookies: {e}")
        return False

if __name__ == '__main__':
    fix_cookies()
