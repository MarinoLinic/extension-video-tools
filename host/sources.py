"""Narrow recovery for older X card links; never guess a different attachment."""
import re
from urllib.parse import urlsplit, urlunsplit


def x_card_fallback_url(url, error):
    if 'Video #1 is unavailable' not in str(error): return None
    parsed=urlsplit(url)
    if parsed.hostname not in ('x.com','www.x.com','twitter.com','www.twitter.com','mobile.twitter.com'): return None
    match=re.fullmatch(r'(/[^/]+/status/\d+)/video/1/?',parsed.path)
    if not match: return None
    return urlunsplit((parsed.scheme,parsed.netloc,match[1],'',''))


def require_single_video(info):
    if not info or info.get('_type') in ('playlist','multi_video') or 'entries' in info:
        raise ValueError('Open the individual video or choose a detected media item.')
    return info


def extract_single_video(ydl,url):
    try: info=ydl.extract_info(url,download=False)
    except Exception as error:
        fallback=x_card_fallback_url(url,error)
        if not fallback: raise
        # Only recover a missing first attachment when the post resolves to one video.
        info=require_single_video(ydl.extract_info(fallback,download=False))
        return info,fallback
    return require_single_video(info),url
