import json
import os
import time
import requests
from dotenv import load_dotenv

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

video_ids = []
if os.path.exists(input_filename):
    with open(input_filename, 'r', encoding='utf-8') as infile:
        for line in infile:
            item = json.loads(line)
            if 'id' in item:
                video_ids.append(int(item['id']))
    print(f'Załadowano {len(video_ids)} filmów z pliku {input_filename}.')
else:
    print(f'Błąd: Plik {input_filename} nie istnieje!')
    exit()

fields = 'id,text,create_time,like_count,parent_comment_id'
comment_url = f'https://open.tiktokapis.com/v2/research/video/comment/list/?fields={fields}'

total_comments_downloaded = 0

with open(output_filename, 'a', encoding='utf-8') as outfile:
    for index, video_id in enumerate(video_ids, start=1):
        print(f'\n[Video {index}/{len(video_ids)}] Pobieranie komentarzy dla video_id: {video_id}')
        
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

print(f'\nPobieranie zakończone! Łącznie pobrano {total_comments_downloaded} komentarzy.')
print(f'Komentarze zostały zapisane do pliku: {output_filename}')