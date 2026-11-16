import csv
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

log = logging.getLogger("recommender")

# Algorithm Recipe (see README): maximum of 10.0 points per song.
ENERGY_POINTS = 3.5
MOOD_POINTS = 2.5
VALENCE_POINTS = 1.5
GENRE_POINTS = 1.5
ACOUSTIC_POINTS = 1.0
MAX_SCORE = ENERGY_POINTS + MOOD_POINTS + VALENCE_POINTS + GENRE_POINTS + ACOUSTIC_POINTS

DEFAULT_VALENCE = 0.6
PREF_KEYS = ("favorite_genre", "favorite_mood", "target_energy", "target_valence", "likes_acoustic")

INT_FIELDS = ("id",)
FLOAT_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")
TEXT_FIELDS = ("title", "artist", "genre", "mood")
UNIT_FIELDS = ("energy", "valence", "danceability", "acousticness")  # must lie in [0, 1]


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_valence: Optional[float] = None  # None -> DEFAULT_VALENCE, and we say so

    def __post_init__(self):
        # Fail loudly on impossible input; record (don't hide) any assumption made.
        for name in ("target_energy", "target_valence"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1, got {value!r}")
        self.valence_assumed = self.target_valence is None
        if self.valence_assumed:
            log.warning("target_valence not given; assuming %.1f", DEFAULT_VALENCE)
            self.target_valence = DEFAULT_VALENCE

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    @staticmethod
    def _prefs(user: UserProfile) -> Dict:
        """Convert a UserProfile into the prefs dict that score_song expects."""
        return {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "target_valence": user.target_valence,
            "likes_acoustic": user.likes_acoustic,
        }

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the k highest-scoring Songs for this user, best first."""
        prefs = self._prefs(user)
        ranked = sorted(
            self.songs,
            key=lambda s: (-score_song(prefs, asdict(s))[0], s.title),
        )
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a one-line text explanation of why this song scored as it did."""
        score, reasons = score_song(self._prefs(user), asdict(song))
        text = f"Score {score:.2f}/{MAX_SCORE:.0f}: " + "; ".join(reasons)
        if user.valence_assumed:
            text += f"; note: valence target not given, assumed {DEFAULT_VALENCE}"
        return text

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV into dicts. Fails loudly (with the line number) on bad data."""
    songs: List[Dict] = []
    try:
        f = open(csv_path, newline="", encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Song catalog not found: {csv_path}") from None
    with f:
        reader = csv.DictReader(f)
        missing = set(INT_FIELDS + FLOAT_FIELDS + TEXT_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{csv_path} is missing columns: {sorted(missing)}")
        for line, row in enumerate(reader, start=2):  # line 1 is the header
            try:
                for field in INT_FIELDS:
                    row[field] = int(row[field])
                for field in FLOAT_FIELDS:
                    row[field] = float(row[field])
                for field in TEXT_FIELDS:
                    if not (row[field] or "").strip():
                        raise ValueError(f"empty {field!r}")
                for field in UNIT_FIELDS:
                    if not 0.0 <= row[field] <= 1.0:
                        raise ValueError(f"{field}={row[field]} outside [0, 1]")
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{csv_path} line {line}: bad value ({exc})") from exc
            songs.append(row)
    if not songs:
        raise ValueError(f"{csv_path} contains no songs")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song (max MAX_SCORE) against user prefs; return (score, reasons for each point)."""
    score = 0.0
    reasons: List[str] = []

    # Nothing to score against -> refuse, rather than rank everything near zero.
    if not any(k in user_prefs for k in PREF_KEYS):
        raise ValueError(f"user_prefs has none of the expected keys {PREF_KEYS}")
    for key in ("target_energy", "target_valence"):
        if key in user_prefs and not 0.0 <= user_prefs[key] <= 1.0:
            raise ValueError(f"{key} must be between 0 and 1, got {user_prefs[key]!r}")

    # Categorical: all-or-nothing.
    if song["mood"] == user_prefs.get("favorite_mood"):
        score += MOOD_POINTS
        reasons.append(f"mood match: {song['mood']} (+{MOOD_POINTS:.1f})")
    if song["genre"] == user_prefs.get("favorite_genre"):
        score += GENRE_POINTS
        reasons.append(f"genre match: {song['genre']} (+{GENRE_POINTS:.1f})")

    # Numeric: reward closeness to the target, not high/low values.
    def closeness(value: float, target: float, max_points: float) -> float:
        return max_points * (1 - abs(value - target))

    if "target_energy" in user_prefs:
        pts = closeness(song["energy"], user_prefs["target_energy"], ENERGY_POINTS)
        score += pts
        reasons.append(
            f"energy {song['energy']:.2f} vs target "
            f"{user_prefs['target_energy']:.2f} (+{pts:.2f})"
        )

    if "target_valence" in user_prefs:
        pts = closeness(song["valence"], user_prefs["target_valence"], VALENCE_POINTS)
        score += pts
        reasons.append(
            f"valence {song['valence']:.2f} vs target "
            f"{user_prefs['target_valence']:.2f} (+{pts:.2f})"
        )

    if "likes_acoustic" in user_prefs:
        target = 0.8 if user_prefs["likes_acoustic"] else 0.2
        pts = closeness(song["acousticness"], target, ACOUSTIC_POINTS)
        score += pts
        reasons.append(
            f"acousticness {song['acousticness']:.2f} vs target "
            f"{target:.2f} (+{pts:.2f})"
        )

    # A missing target means that feature was NOT scored; say so instead of hiding it.
    for key in ("target_energy", "target_valence", "likes_acoustic"):
        if key not in user_prefs:
            log.warning("%s missing from user_prefs; feature not scored", key)
            reasons.append(f"{key} not given, so that feature was not scored")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song and return the top k as (song, score, explanation), best first."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored.append((song, score, "; ".join(reasons)))

    # sorted() returns a NEW list and leaves `scored` untouched; ties break by title.
    return sorted(scored, key=lambda item: (-item[1], item[0]["title"]))[:k]
