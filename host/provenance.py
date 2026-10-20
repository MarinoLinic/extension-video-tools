"""Small source record shared by media tags and transcript front matter."""
import json
from common import validate_url


def source_metadata(options, info=None, media_urls=()):
    info=info or {}
    def web(value):
        try: return validate_url(value)
        except (ValueError, TypeError): return None
    urls=[]
    for value in media_urls:
        url=web(value)
        if url and url not in urls: urls.append(url)
    return dict(page_url=options.get('page_url') or options['url'],
                source_url=options['url'],
                webpage_url=web(info.get('webpage_url')),
                media_urls=urls)


def media_tags(record):
    lines=[f"Page URL: {record['page_url']}",f"Source URL: {record['source_url']}"]
    if record['webpage_url']: lines.append(f"Video page URL: {record['webpage_url']}")
    lines.extend(f'Media URL: {url}' for url in record['media_urls'])
    return {**{k:v for k,v in record.items() if v and k!='media_urls'},
            'media_urls':json.dumps(record['media_urls'],ensure_ascii=False),
            'purl':record['page_url'],'comment':'\n'.join(lines)}
