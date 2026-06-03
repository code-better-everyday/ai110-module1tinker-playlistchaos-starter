# Playlist Chaos — Bug Fix Summary

This branch (`fix-playlist-chaos-bugs`) fixes six logic bugs in
[`playlist_logic.py`](playlist_logic.py) and adds a test suite
([`test_playlist_logic.py`](test_playlist_logic.py)) that covers all of them.

## How to run

```bash
# install deps (Streamlit)
pip install -r requirements.txt

# run the tests (no external test deps required)
python test_playlist_logic.py

# run the app
streamlit run app.py
```

The test suite has **25 assertions** and exits non-zero if any fail.

## Bugs fixed

| # | Function | Symptom | Fix |
|---|----------|---------|-----|
| 1 | `compute_playlist_stats` | `hype_ratio` was always `1.0` because it divided by `len(hype)` | Divide by total song count (`len(all_songs)`) |
| 2 | `compute_playlist_stats` | `avg_energy` summed only Hype songs but divided by the count of all songs | Sum energy over all songs |
| 3 | `search_songs` | Search rarely matched — the substring check was reversed (`value in q`) | Check `q in value` so a field that *contains* the query matches |
| 4 | `random_choice_or_none` | Raised `IndexError` on an empty list despite its name | Return `None` when the list is empty |
| 5 | `merge_playlists` | Mutated the caller's input list as a side effect (aliased `a`'s list, then `extend`ed it) | Copy the list before extending |
| 6 | `classify_song` | Chill keywords were matched against `title` (never lowercased) instead of `genre`, so chill detection rarely fired | Match chill keywords against `genre`, symmetric with hype keywords |
| 7 | `add_song_sidebar` (app.py) | Blank/whitespace-only Title or Artist could be saved — the guard checked raw input (`"   "` is truthy) but normalization stripped it to `""` | Validate `title.strip()`/`artist.strip()`, reject with a warning, and show a success message on add |

## Detail

### 1 & 2 — `compute_playlist_stats`
```python
# before
total = len(hype)
...
total_energy = sum(song.get("energy", 0) for song in hype)
avg_energy = total_energy / len(all_songs)

# after
total = len(all_songs)
...
total_energy = sum(song.get("energy", 0) for song in all_songs)
avg_energy = total_energy / len(all_songs)
```

### 3 — `search_songs`
```python
# before
if value and value in q:

# after
if value and q in value:
```

### 4 — `random_choice_or_none`
```python
# after
if not songs:
    return None
return random.choice(songs)
```

### 5 — `merge_playlists`
```python
# before
merged[key] = a.get(key, [])

# after
merged[key] = list(a.get(key, []))
```

### 6 — `classify_song`
```python
# before
is_chill_keyword = any(k in title for k in chill_keywords)

# after
is_chill_keyword = any(k in genre for k in chill_keywords)
```

### 7 — `add_song_sidebar` (app.py)
```python
# before
if title and artist:          # "   " is truthy, slips through
    normalized = normalize_song(song)
    ...

# after
if not title.strip() or not artist.strip():
    st.sidebar.warning("Title and Artist are required.")
    return
normalized = normalize_song(song)
...
st.sidebar.success(f"Added \"{normalized['title']}\" by {normalized['artist']}.")
```

