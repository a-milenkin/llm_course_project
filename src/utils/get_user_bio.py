import asyncio
# import requests
import re
import aiohttp
from lxml.html import fromstring

async def get_bio_text(username = 'EstrellaMoretti'):
    
    url = f'https://t.me/{username}'  

    async with aiohttp.ClientSession() as session:
        async with session.post(url) as response:
            
            soup = fromstring(await response.text())
            xpath = '/html/body/div[2]/div[2]/div/div[4]'
            try: text = soup.xpath(xpath)[0].text  
            except: text = ''
            return text

async def remove_urls_findall(text, replacement_dict={'tg':"telegram_channel", "url": 'link'}):
    tg_pattern = re.compile(r'https?://t.me\S+|t.me\S+|@\S+')
    url_pattern = re.compile(r'https?://\S+|www\.\S+|t.me\S+')

    urls = tg_pattern.findall(text)
    for url in urls:
        text = text.replace(url, replacement_dict['tg'])

    urls = url_pattern.findall(text)
    for url in urls:
        text = text.replace(url, replacement_dict['url'])
    
    return f'{text}'
