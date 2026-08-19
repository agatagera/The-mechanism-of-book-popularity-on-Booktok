import json
import os
import time
import requests
import re
from dotenv import load_dotenv

# book dictionary with keywords for each book from 2.top_books.ipnyb
BOOKS_DICT = {
    'Trylogia Hell': [
        'trylogiahell', 'pizgaczhell', 'katarzynabarlińska', 'katarzynabarlinska', 
        'pizgacz', 'victoriaclark', 'nathanielshey'
    ],
    'Purple Rain': [
        'purplerain', 'joannabalicka', 'stormisullivan', 'aceweston'
    ],
    'I Wanna Fall': [
        'iwannafall', 'juliapopiel', 'aidenscott'
    ],
    'Rodzina Monet': [
        'rodzinamonet', 'wersowmonet'
    ],
    'Seria Hellish': [
        'seriahellish', 'hellish', 'weronikaplota'
    ],
    'Co wyszeptał nam deszcz': [
        'cowyszeptałnamdeszcz', 'cowyszeptalnamdeszcz', 'monikarutka'
    ],
    'Red Lies': [
        'redlies', 'izabellanowaczyk'
    ],
    'Seria Agony': [
        'whiteagony', 'darkagony', 'aleksandranil'
    ],
    'Fourth Wing': [
        'fourthwing', 'rebeccayarros'
    ],
    'Boys of Tommen': [
        'boysoftommen', 'chloewalsh'
    ],
    'ACOTAR': [
        'acotar', 'sarahjmaas'
    ]
}

def identify_book(item):
    desc = str(item.get('video_description', '')) if item.get('video_description') is not None else ''
    voice = str(item.get('voice_to_text', '')) if item.get('voice_to_text') is not None else ''
    tags = item.get('hashtag_names', [])
    tags_str = ' '.join([str(t) for t in tags]) if isinstance(tags, list) else str(tags or '')
    
    full_text = f"{desc} {voice} {tags_str}".lower()
    
    for book_title, keywords in BOOKS_DICT.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', full_text):
                return book_title
    return None

def get_access_token():
    load_dotenv(override=True)
    client_key = os.getenv("TIKTOK_CLIENT_KEY", "").strip(" \"'")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "").strip(" \"'")

    auth_url = 'https://open.tiktokapis.com/v2/oauth/token/'
    auth_response = requests.post(
        auth_url,
        data={
            'client_key': client_key,
            'client_secret': client_secret,
            'grant_type': 'client_credentials',
        },
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cache-Control': 'no-cache',
        },
        timeout=30
    )
    auth_response.raise_for_status()
    token = auth_response.json().get('access_token')
    print('Token dostępu pobrany pomyślnie!')
    return token

access_token = get_access_token()

input_filename = 'tiktok_booktok_2025_data.jsonl'
output_filename = 'tiktok_booktok_2025_comments.jsonl'

# Filtering videos based on BOOKS_DICT
target_videos = []
if os.path.exists(input_filename):
    with open(input_filename, 'r', encoding='utf-8') as infile:
        for line in infile:
            item = json.loads(line)
            if 'id' in item:
                book_matched = identify_book(item)
                if book_matched:
                    target_videos.append((int(item['id']), book_matched))
    print(f'Zakwalifikowano {len(target_videos)} filmów pasujących do książek z BOOKS_DICT.')
else:
    print(f'Błąd: Plik {input_filename} nie istnieje!')
    exit()

fields = 'id,text,create_time,like_count,parent_comment_id'
comment_url = f'https://open.tiktokapis.com/v2/research/video/comment/list/?fields={fields}'

total_comments_downloaded = 0

with open(output_filename, 'a', encoding='utf-8') as outfile:
    for index, (video_id, book_title) in enumerate(target_videos, start=1):
        print(f'\n[Video {index}/{len(target_videos)}] ID: {video_id} | Książka: {book_title}')
        
        cursor = 0
        has_more = True
        video_comments_count = 0
        max_comments_per_video = 500  

        while has_more and video_comments_count < max_comments_per_video:
            payload_comment = {
                'video_id': video_id,
                'max_count': 100,
                'cursor': cursor
            }

            max_retries = 3
            success = False

            for attempt in range(1, max_retries + 1):
                try:
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json',
                    }
                    
                    res = requests.post(
                        comment_url, headers=headers, json=payload_comment, timeout=30
                    )

                    if res.status_code in (401, 403):
                        print('Token wygasł! Odświeżanie tokena...')
                        access_token = get_access_token()
                        continue

                    if res.status_code != 200:
                        print(f'Błąd HTTP {res.status_code} dla video_id {video_id} (próba {attempt}/{max_retries}): {res.text}')
                        time.sleep(5)
                        continue

                    res_data = res.json()
                    data = res_data.get('data', {})
                    comments = data.get('comments', [])

                    if not comments:
                        has_more = False
                        success = True
                        break

                    for comment in comments:
                        comment['video_id'] = video_id
                        comment['book_title'] = book_title  # Attaching the title directly to the comment record
                        outfile.write(json.dumps(comment, ensure_ascii=False) + '\n')
                    outfile.flush()

                    fetched_batch = len(comments)
                    video_comments_count += fetched_batch
                    total_comments_downloaded += fetched_batch

                    has_more = data.get('has_more', False)
                    cursor = data.get('cursor', cursor + fetched_batch)

                    print(f'Pobrano {fetched_batch} komentarzy (Łącznie dla wideo: {video_comments_count})')

                    success = True
                    time.sleep(1.5)  # Rate Limit Protection
                    break

                except Exception as e:
                    print(f'Wyjątek połączenia (Próba {attempt}/{max_retries}): {e}')
                    time.sleep(5)

            if not success:
                print(f'Nie udało się pobrać komentarzy dla video_id {video_id}. Przejście do kolejnego filmu.')
                break

print(f'\nPobieranie zakończone! Łącznie pobrano {total_comments_downloaded} komentarzy dla dopasowanych książek.')
print(f'Plik wyjściowy: {output_filename}')