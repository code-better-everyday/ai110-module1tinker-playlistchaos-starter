"""Tests for playlist_logic.

Run from the playlistchaos directory:
    python test_playlist_logic.py

Each test asserts the *correct* (expected) behavior. Before the bug fixes
several of these fail; after the fixes they should all pass.
"""

import copy

from playlist_logic import (
    DEFAULT_PROFILE,
    build_playlists,
    classify_song,
    compute_playlist_stats,
    lucky_pick,
    merge_playlists,
    most_common_artist,
    normalize_song,
    random_choice_or_none,
    search_songs,
)


# --- tiny test harness ---------------------------------------------------

_FAILURES = []
_PASSES = 0


def check(name, cond, detail=""):
    global _PASSES
    if cond:
        _PASSES += 1
        print(f"  PASS: {name}")
    else:
        _FAILURES.append(name)
        print(f"  FAIL: {name}  {detail}")


def run(test_fn):
    print(f"\n[{test_fn.__name__}]")
    try:
        test_fn()
    except Exception as exc:  # a crash is also a failure
        _FAILURES.append(test_fn.__name__)
        print(f"  FAIL (raised): {test_fn.__name__} -> {exc!r}")


# --- fixtures ------------------------------------------------------------

def sample_songs():
    return [
        {"title": "Thunderstruck", "artist": "AC/DC", "genre": "rock", "energy": 9, "tags": ["classic"]},
        {"title": "Lo-fi Rain", "artist": "DJ Calm", "genre": "lofi", "energy": 2, "tags": ["study"]},
        {"title": "Night Drive", "artist": "Neon Echo", "genre": "electronic", "energy": 6, "tags": ["synth"]},
        {"title": "Soft Piano", "artist": "Sleep Sound", "genre": "ambient", "energy": 1, "tags": ["sleep"]},
        {"title": "Bohemian Rhapsody", "artist": "Queen", "genre": "rock", "energy": 8, "tags": ["classic"]},
    ]


# --- compute_playlist_stats (bugs 1 & 2) ---------------------------------

def test_stats_total_and_ratio():
    profile = dict(DEFAULT_PROFILE)
    playlists = build_playlists(sample_songs(), profile)
    stats = compute_playlist_stats(playlists)

    hype = len(playlists["Hype"])
    chill = len(playlists["Chill"])
    mixed = len(playlists["Mixed"])
    total = hype + chill + mixed

    check("total_songs counts every song", stats["total_songs"] == total,
          f"got {stats['total_songs']}, expected {total}")
    check("counts add up to total", hype + chill + mixed == total)

    expected_ratio = hype / total if total else 0.0
    check("hype_ratio = hype / total_songs",
          abs(stats["hype_ratio"] - expected_ratio) < 1e-9,
          f"got {stats['hype_ratio']}, expected {expected_ratio}")
    check("hype_ratio is not stuck at 1.0 when mixed/chill exist",
          stats["hype_ratio"] < 1.0 or total == hype)


def test_stats_avg_energy():
    profile = dict(DEFAULT_PROFILE)
    playlists = build_playlists(sample_songs(), profile)
    stats = compute_playlist_stats(playlists)

    all_songs = playlists["Hype"] + playlists["Chill"] + playlists["Mixed"]
    expected_avg = sum(s["energy"] for s in all_songs) / len(all_songs)

    check("avg_energy averages over ALL songs",
          abs(stats["avg_energy"] - expected_avg) < 1e-9,
          f"got {stats['avg_energy']}, expected {expected_avg}")


def test_stats_empty():
    empty = {"Hype": [], "Chill": [], "Mixed": []}
    stats = compute_playlist_stats(empty)
    check("empty: total_songs == 0", stats["total_songs"] == 0)
    check("empty: hype_ratio == 0.0", stats["hype_ratio"] == 0.0)
    check("empty: avg_energy == 0.0", stats["avg_energy"] == 0.0)


# --- search_songs (bug 3) ------------------------------------------------

def test_search_finds_substring():
    songs = sample_songs()
    res = search_songs(songs, "queen", field="artist")
    check("search 'queen' finds Bohemian Rhapsody",
          any(s["title"] == "Bohemian Rhapsody" for s in res),
          f"got {[s['title'] for s in res]}")


def test_search_partial_and_case():
    songs = sample_songs()
    res = search_songs(songs, "ac", field="artist")  # AC/DC
    check("partial+case-insensitive 'ac' finds AC/DC",
          any(s["artist"] == "AC/DC" for s in res),
          f"got {[s['artist'] for s in res]}")


def test_search_empty_query_returns_all():
    songs = sample_songs()
    check("empty query returns all songs",
          len(search_songs(songs, "")) == len(songs))


def test_search_no_match():
    songs = sample_songs()
    check("non-matching query returns nothing",
          search_songs(songs, "zzzznomatch", field="artist") == [])


# --- random_choice_or_none / lucky_pick (bug 4) --------------------------

def test_random_choice_empty_is_none():
    check("random_choice_or_none([]) returns None",
          random_choice_or_none([]) is None)


def test_random_choice_nonempty():
    only = [{"title": "X"}]
    check("random_choice_or_none picks from a 1-item list",
          random_choice_or_none(only) == {"title": "X"})


def test_lucky_pick_empty_mode_is_none():
    empty = {"Hype": [], "Chill": [], "Mixed": []}
    check("lucky_pick on empty 'hype' returns None",
          lucky_pick(empty, mode="hype") is None)
    check("lucky_pick on empty 'any' returns None",
          lucky_pick(empty, mode="any") is None)


# --- merge_playlists (bug 5) ---------------------------------------------

def test_merge_does_not_mutate_inputs():
    a = {"Hype": [{"title": "A"}], "Chill": []}
    b = {"Hype": [{"title": "B"}], "Chill": [{"title": "C"}]}
    a_before = copy.deepcopy(a)
    b_before = copy.deepcopy(b)

    merged = merge_playlists(a, b)

    check("merge does not mutate input a", a == a_before, f"a became {a}")
    check("merge does not mutate input b", b == b_before, f"b became {b}")
    check("merged Hype has both songs", len(merged["Hype"]) == 2,
          f"got {len(merged['Hype'])}")
    check("merged Chill has one song", len(merged["Chill"]) == 1)


def test_merge_with_empty():
    a = {"Hype": [{"title": "A"}], "Chill": [], "Mixed": []}
    merged = merge_playlists(a, {})
    check("merge with {} preserves all songs", len(merged["Hype"]) == 1)
    check("merge with {} does not mutate a", len(a["Hype"]) == 1)


# --- classify_song (bug 6) -----------------------------------------------

def test_classify_chill_genre_keyword():
    # ambient is a chill keyword; energy 5 is above chill_max(3) and below
    # hype_min(7), and ambient != favorite genre -> should be Chill.
    profile = dict(DEFAULT_PROFILE)
    song = normalize_song(
        {"title": "Drifting", "artist": "X", "genre": "ambient", "energy": 5}
    )
    check("ambient (energy 5) classifies as Chill",
          classify_song(song, profile) == "Chill",
          f"got {classify_song(song, profile)}")


def test_classify_hype_genre_keyword():
    profile = dict(DEFAULT_PROFILE)
    song = normalize_song(
        {"title": "Riff", "artist": "X", "genre": "punk", "energy": 5}
    )
    check("punk (energy 5) classifies as Hype",
          classify_song(song, profile) == "Hype",
          f"got {classify_song(song, profile)}")


def test_classify_mixed():
    profile = dict(DEFAULT_PROFILE)
    song = normalize_song(
        {"title": "Cool Jazz", "artist": "X", "genre": "jazz", "energy": 5}
    )
    check("mid-energy jazz classifies as Mixed",
          classify_song(song, profile) == "Mixed",
          f"got {classify_song(song, profile)}")


# --- run everything ------------------------------------------------------

def main():
    tests = [
        test_stats_total_and_ratio,
        test_stats_avg_energy,
        test_stats_empty,
        test_search_finds_substring,
        test_search_partial_and_case,
        test_search_empty_query_returns_all,
        test_search_no_match,
        test_random_choice_empty_is_none,
        test_random_choice_nonempty,
        test_lucky_pick_empty_mode_is_none,
        test_merge_does_not_mutate_inputs,
        test_merge_with_empty,
        test_classify_chill_genre_keyword,
        test_classify_hype_genre_keyword,
        test_classify_mixed,
    ]
    for t in tests:
        run(t)

    print("\n" + "=" * 50)
    print(f"PASSED: {_PASSES}   FAILED: {len(_FAILURES)}")
    if _FAILURES:
        print("Failing tests:")
        for name in _FAILURES:
            print(f"  - {name}")
    print("=" * 50)
    return 1 if _FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
