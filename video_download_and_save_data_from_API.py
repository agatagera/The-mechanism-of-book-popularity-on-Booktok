import json
import os
import time
from datetime import date, timedelta
import requests
from dotenv import load_dotenv

# 1. Function to retrieve the access_token
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
    print('Access token successfully retrieved!')
    return token

# First retriving the token 
access_token = get_access_token()

# 2. Creatie API Request 
fields = 'id,video_description,create_time,region_code,share_count,view_count,like_count,comment_count,music_id,hashtag_names,username,effect_ids,playlist_id,voice_to_text,is_stem_verified,favorites_count,video_duration,hashtag_info_list,sticker_info_list,effect_info_list,video_mention_list,video_label,video_tag'
query_url = f'https://open.tiktokapis.com/v2/research/video/query/?fields={fields}'

# 3. Date range: 2025.01.01 - 2025.12.31
start_date = date(2025, 1, 1)
end_date = date(2025, 12, 31)
delta = timedelta(days=1)

output_filename = 'tiktok_booktok_2025_data.jsonl'
total_downloaded = 0
current_date = start_date

# 4. Main loop and writing to a JSONL file
with open(output_filename, 'a', encoding='utf-8') as outfile:
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        print(f'\n *** Downloads for the day: {date_str} ***')

        day_videos_count = 0
        max_records_per_day = 100
        cursor = 0
        search_id = None
        has_more = True

        while day_videos_count < max_records_per_day and has_more:
            payload_video = {
                'query': {
                    'and': [
                        {
                            'operation': 'IN',
                            'field_name': 'region_code',
                            'field_values': ['PL'],
                        },
                        {
                            'operation': 'EQ',
                            'field_name': 'hashtag_name',
                            'field_values': ['booktok'],
                        },
                    ]
                },
                'max_count': 100,
                'start_date': date_str,
                'end_date': date_str,
                'cursor': cursor,
            }

            if search_id:
                payload_video['search_id'] = search_id

            # Retry Loop. Provides 3 chances in case of network errors or 500 server errors
            max_retries = 3
            success = False

            for attempt in range(1, max_retries + 1):
                try:
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json',
                    }
                    
                    res = requests.post(
                        query_url, headers=headers, json=payload_video, timeout=30
                    )

                    # If the token has expired (401 / 403 error), refresh it 
                    if res.status_code in (401, 403):
                        print('The token has expired! Refreshing the token.')
                        access_token = get_access_token()
                        continue

                    # If the server returned a 500 error (internal error),wait and try again
                    if res.status_code != 200:
                        print(f'Error HTTP {res.status_code} dla {date_str} (attempt {attempt}/{max_retries}): {res.text}')
                        time.sleep(5)
                        continue

                    res_data = res.json()
                    data = res_data.get('data', {})
                    videos = data.get('videos', [])

                    if not videos:
                        print(f'No more videos for the day: {date_str}.')
                        has_more = False
                        success = True
                        break

                    # Write records to the file
                    for video in videos:
                        outfile.write(json.dumps(video, ensure_ascii=False) + '\n')
                    outfile.flush() 

                    fetched_batch = len(videos)
                    day_videos_count += fetched_batch
                    total_downloaded += fetched_batch

                    # Update parameters
                    has_more = data.get('has_more', False)
                    cursor = data.get('cursor', cursor + fetched_batch)
                    search_id = data.get('search_id')

                    print( f'Downloaded {fetched_batch} records (Total for the day: {day_videos_count}/{max_records_per_day})')

                    success = True
                    time.sleep(1.5) # Rate Limit Protection
                    break 

                except Exception as e:
                    print(f'Exception during connection (Attempt {attempt}/{max_retries}): {e}')
                    time.sleep(5)

            # If the error persists after 3 attempts, move on to the next day
            if not success:
                print(f'Retrieve error for the day: {date_str}. Move on to the next day.')
                break

        current_date += delta

print(f'Download complete! Total downloaded: {total_downloaded} records.')
print(f'The data has been saved to the file: {output_filename}')