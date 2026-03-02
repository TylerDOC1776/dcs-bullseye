import yt_dlp

# Exact bot options but with verbose on so we can see what's happening
opts = {
    'format': 'best',
    'noplaylist': True,
    'verbose': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'cookiefile': r'C:\Musicbot\cookies.txt',
    'js_runtimes': {'node': {}},
    'remote_components': 'ejs:github',
    'extractor_args': {'youtube': {'player_client': ['ios', 'web']}},
}

urls = [
    'https://www.youtube.com/watch?v=T3rXdeOvhNE',  # Nickelback - Photograph
    'https://www.youtube.com/watch?v=Aiay8I5IPB8',  # Nickelback - How You Remind Me
    'https://www.youtube.com/watch?v=0fZyNUikfEM',  # Animals
]

with yt_dlp.YoutubeDL(opts) as ydl:
    for url in urls:
        try:
            info = ydl.extract_info(url, download=False)
            print('SUCCESS:', info.get('title'), '| format:', info.get('ext'), info.get('format_id'))
        except Exception as e:
            print('FAILED:', url.split('=')[-1], e)
