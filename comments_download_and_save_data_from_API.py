import pandas as pd
import re

# Wczytanie bazy
df = pd.read_json('tiktok_booktok_2025_data.jsonl', lines=True)

# 1. Definicja słownika badanych książek i odpowiadających im fraz/hashtagów
# UWAGA: Podawaj frazy małymi literami
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

# 2. Bezpieczne łączenie kolumn tekstowych
def create_full_text(row):
    desc = str(row['video_description']) if pd.notna(row['video_description']) else ''
    voice = str(row['voice_to_text']) if pd.notna(row['voice_to_text']) else ''
    
    hashtags = row['hashtag_names']
    if isinstance(hashtags, list):
        tags = ' '.join([str(tag) for tag in hashtags])
    else:
        tags = str(hashtags) if pd.notna(hashtags) else ''
        
    return f"{desc} {voice} {tags}".lower()

df['full_text'] = df.apply(create_full_text, axis=1)

# 3. Funkcja wyszukująca dopasowania
def assign_book_title(text):
    found_titles = []
    for title, keywords in BOOKS_DICT.items():
        for kw in keywords:
            # \b oznacza granicę słowa – zapobiega błędnym dopasowaniom wewnątrz innych wyrazów
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, text):
                found_titles.append(title)
                break  # Znaleziono frazę dla tej książki, przejdź do następnej w słowniku
                
    if not found_titles:
        return 'Inny / Brak'
    elif len(found_titles) == 1:
        return found_titles[0]
    else:
        return 'Zestawienie (Wiele książek)'  # Filmy typu "Top 5 książek na wakacje"

# 4. Utworzenie nowej kolumny
df['book_title'] = df['full_text'].apply(assign_book_title)

# Sprawdzenie rozkładu przypisanych książek w Twojej bazie
print("=== ROZKŁAD POBRANYCH REKORDÓW PER KSIĄŻKA ===")
print(df['book_title'].value_counts())