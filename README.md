# 🎵 Music Recommender Assistant (RAG + Reliability Testing)

**Original project (Modules 1-3): Music Recommender Simulation.** A small, content-based music recommender. It represented songs (genre, mood, energy, valence, acousticness) and a hand-written "taste profile" as data, scored every song in an 18-song catalog against that profile with a weighted rule, and printed a ranked top-5 with a plain-English reason for each pick. Its goals were to make the scoring logic explainable and to stress-test it with adversarial profiles (see the [appendix](#appendix-original-recommender-details-modules-1-3)).

## Title and Summary

**This project extends that recommender into a natural-language assistant.** Instead of hand-writing a numeric profile, you type a request such as *"something to study to on a rainy day"*. The assistant **retrieves** matching entries from a knowledge base of genre, mood and activity descriptions, turns those entries into a taste profile, and ranks songs with the original scoring engine. The retrieved entries are shown with every answer, so each recommendation can be traced to the evidence behind it.

Why it matters: recommenders usually hide how a request becomes a result. Here every step (guardrail, retrieval, profile, score, self-check) is visible, logged and tested, which makes it easy to see where the system is right, uncertain or wrong. It runs fully offline with no API key, so results are reproducible.

## Architecture Overview

The full diagram is in [diagrams/system_diagram.mmd](diagrams/system_diagram.mmd) (Mermaid source).

```
request -> 1 guardrails -> 2 retriever -> 3 profile builder -> 4 scorer/ranker -> 5 self-check -> output
                               ^                                      ^
                     knowledge_base.json                         songs.csv
```

1. **Guardrails** reject empty, non-text or over-300-character input.
2. **Retriever** (`src/assistant.py`) matches whole words and phrases against 25 knowledge-base docs and keeps the top 3.
3. **Profile builder** turns the retrieved docs' hints into genre, mood, energy, valence and acoustic targets (score-weighted average for numbers). This is where retrieval changes behavior: no retrieved docs means no meaningful profile.
4. **Scorer/ranker** (`src/recommender.py`) is the original engine, unchanged.
5. **Self-check** flags unmatched requests (neutral profile, 0% confidence) and weak best matches (top score under 60% of the maximum).

Humans and tests check the output at two points: the user reads the retrieved context and per-song reasons (and `logs/assistant.log` keeps an audit trail), and `src/evaluate.py` plus pytest check the pipeline automatically. A failing check sends the developer back to fix the knowledge base or scoring.

## Setup Instructions

Requires Python 3.10+ (developed on 3.12).

```bash
git clone https://github.com/mlaya413/applied-ai-system-project.git
cd applied-ai-system-project

python -m venv .venv
source .venv/bin/activate          # Mac/Linux
.venv\Scripts\activate             # Windows

pip install -r requirements.txt

python -m src.assistant "something to study to on a rainy day"   # one request
python -m src.assistant                                          # interactive (blank line quits)
python -m src.evaluate                                           # reliability harness
python -m pytest                                                 # unit tests
python -m src.main                                               # original profile-based runner
```

Run all commands from the repository root. Logs are written to `logs/assistant.log`.

## Sample Interactions

Output is trimmed to the top results; run the commands to see everything.

**1. Activity request** - `python -m src.assistant "gym workout"`

```
Retrieved context:
  - [activity-workout] Workouts need high energy and a driving beat; acoustic sounds feel too soft.
Profile built from context: genre=None, mood=intense, energy=0.90, valence=0.65, acoustic=False
Confidence: 54%
#1 Storm Runner - Voltline [rock/intense] 8.11/10
     mood match: intense (+2.5); energy 0.91 vs target 0.90 (+3.46); valence 0.48 vs target 0.65 (+1.24); ...
#2 Gym Hero - Max Pulse [pop/intense] 8.06/10
```

**2. Several docs combined** - `python -m src.assistant "late night drive with neon synthwave"`

```
Retrieved context:
  - [genre-synthwave] Synthwave is moody, retro and synth-heavy with medium-high energy.
  - [activity-drive] Driving music is medium-high energy and engaging.
Profile built from context: genre=synthwave, mood=moody, energy=0.70, valence=0.48, acoustic=False
Confidence: 98%
#1 Night Drive Loop - Neon Echo [synthwave/moody] 9.79/10
```

**3. Unmatched input (guardrail fallback)** - `python -m src.assistant "qwerty zzz"`

```
Retrieved context:
  (none)
Profile built from context: genre=None, mood=None, energy=0.50, valence=0.50, acoustic=False
Confidence: 0%
WARNING: No knowledge-base match; using a neutral profile. Try naming a genre, mood or activity.
WARNING: Best match scored only 5.4/10; the catalog may not fit this request.
```

**4. Rejected input** - `python -m src.assistant ""` prints `Input rejected: Please describe what you want to listen to.` and exits with code 1.

## Execution Evidence

Every block below is real, unedited output captured on 2026-11-16 (Python 3.12, Windows) by running the commands from the repository root. The same text is saved in [evidence/](evidence/): `sample_runs.txt`, `evaluate.txt`, `pytest.txt`, and `assistant_log_excerpt.txt`. Long recommendation lists are cut to the top results with `head`. Results are deterministic, so you should get identical output.

### A. End-to-end runs (input -> retrieval -> profile -> ranked output)

These show the RAG behavior: different requests retrieve different knowledge-base entries, which produce different profiles and different top songs.

```text
$ python -m src.assistant "something to study to on a rainy day"

Request: "something to study to on a rainy day"
Retrieved context:
  - [mood-focused] Focus music is steady, low-to-medium energy and not distracting.
  - [mood-sad] Sad listening wants low valence and usually lower energy.
Profile built from context: genre=None, mood=focused, energy=0.35, valence=0.40, acoustic=True
Confidence: 53%
#1 Focus Flow - LoRoom [lofi/focused] 8.02/10
     mood match: focused (+2.5); energy 0.40 vs target 0.35 (+3.32); valence 0.59 vs target 0.40 (+1.22); acousticness 0.78 vs target 0.80 (+0.98)
#2 Library Rain - Paper Lanterns [lofi/chill] 5.64/10
     energy 0.35 vs target 0.35 (+3.50); valence 0.60 vs target 0.40 (+1.20); acousticness 0.86 vs target 0.80 (+0.94)
#3 Autumn Letters - Fern & Ash [folk/melancholic] 5.49/10
     energy 0.30 vs target 0.35 (+3.32); valence 0.25 vs target 0.40 (+1.27); acousticness 0.91 vs target 0.80 (+0.89)
#4 Midnight Coding - LoRoom [lofi/chill] 5.42/10

$ python -m src.assistant "gym workout"

Request: "gym workout"
Retrieved context:
  - [activity-workout] Workouts need high energy and a driving beat; acoustic sounds feel too soft.
Profile built from context: genre=None, mood=intense, energy=0.90, valence=0.65, acoustic=False
Confidence: 54%
#1 Storm Runner - Voltline [rock/intense] 8.11/10
     mood match: intense (+2.5); energy 0.91 vs target 0.90 (+3.46); valence 0.48 vs target 0.65 (+1.24); acousticness 0.10 vs target 0.20 (+0.90)
#2 Gym Hero - Max Pulse [pop/intense] 8.06/10
     mood match: intense (+2.5); energy 0.93 vs target 0.90 (+3.40); valence 0.77 vs target 0.65 (+1.32); acousticness 0.05 vs target 0.20 (+0.85)
#3 Concrete Crown - Kid Meridian [hip hop/confident] 5.42/10
     energy 0.78 vs target 0.90 (+3.08); valence 0.62 vs target 0.65 (+1.46); acousticness 0.08 vs target 0.20 (+0.88)
#4 Sunrise City - Neon Echo [pop/happy] 5.41/10
     energy 0.82 vs target 0.90 (+3.22); valence 0.84 vs target 0.65 (+1.22); acousticness 0.18 vs target 0.20 (+0.98)

$ python -m src.assistant "qwerty zzz"

Request: "qwerty zzz"
Retrieved context:
  (none)
Profile built from context: genre=None, mood=None, energy=0.50, valence=0.50, acoustic=False
Confidence: 0%
WARNING: No knowledge-base match; using a neutral profile. Try naming a genre, mood or activity.
WARNING: Best match scored only 5.4/10; the catalog may not fit this request.
#1 Velvet Hours - Satin Avenue [r&b/romantic] 5.35/10
     energy 0.55 vs target 0.50 (+3.32); valence 0.72 vs target 0.50 (+1.17); acousticness 0.34 vs target 0.20 (+0.86)
#2 Dusty Porchlight - Wren Hollow [country/nostalgic] 5.12/10
     energy 0.52 vs target 0.50 (+3.43); valence 0.68 vs target 0.50 (+1.23); acousticness 0.74 vs target 0.20 (+0.46)
#3 Midnight Coding - LoRoom [lofi/chill] 5.12/10
     energy 0.42 vs target 0.50 (+3.22); valence 0.56 vs target 0.50 (+1.41); acousticness 0.71 vs target 0.20 (+0.49)
```

What to notice: the study request retrieved two docs (`mood-focused`, `mood-sad`) and built `energy=0.35, valence=0.40`; the gym request retrieved one doc and built `energy=0.90`; the nonsense request retrieved nothing. The top song changes from Focus Flow (lofi) to Storm Runner (rock) to a neutral low-confidence list, and each reason line shows the exact points earned.

### B. Guardrail behavior

```text
$ python -m src.assistant ""
Input rejected: Please describe what you want to listen to.
(exit code 1)

$ python -m src.assistant "<400 x characters>"
Input rejected: Request too long (400 chars; max 300).
```

The unmatched request in section A also shows the fallback guardrail: neutral profile, `Confidence: 0%`, and two warnings instead of a crash or a silent answer.

### C. Reliability evaluation: `python -m src.evaluate`

```text
[PASS] 'I need something to study to'               study -> focused/chill on top
[PASS] 'pump me up for the gym'                     gym -> energy >= 0.8
[PASS] 'sad rainy day music'                        sad -> low energy
[PASS] 'late night drive with neon synthwave'       synthwave named -> synthwave #1
[PASS] 'help me fall asleep'                        sleep -> acoustic
[PASS] "let's party and dance"                      party -> high energy
[PASS] 'gibberish xyzzy'                            unknown -> warning, zero confidence
[PASS] guardrail rejects ''
[PASS] guardrail rejects '   '
[PASS] guardrail rejects 'xxxxxxxxxxxxxxxxxxxx'
[PASS] guardrail rejects 'None'
[PASS] guardrail rejects '42'

12/12 passed; mean confidence 51%
exit 0
```

Seven labelled requests (each also re-run to confirm identical ranking) and five invalid inputs that must be rejected. The process exits 0 only if every check passes, so it can gate CI.

### D. Unit tests: `python -m pytest -v`

```text
platform win32 -- Python 3.12.10, pytest-9.2.0
collecting ... collected 7 items

tests/test_assistant.py::test_rejects_bad_input PASSED                   [ 14%]
tests/test_assistant.py::test_retrieval_whole_word_only PASSED           [ 28%]
tests/test_assistant.py::test_retrieved_docs_change_profile PASSED       [ 42%]
tests/test_assistant.py::test_retrieval_changes_recommendations PASSED   [ 57%]
tests/test_assistant.py::test_no_match_falls_back_safely PASSED          [ 71%]
tests/test_recommender.py::test_recommend_returns_songs_sorted_by_score PASSED [ 85%]
tests/test_recommender.py::test_explain_recommendation_returns_non_empty_string PASSED [100%]

============================== 7 passed in 0.05s ==============================
```

### E. Audit log: `logs/assistant.log`

Each request records the retrieved docs, the profile built from them, the top songs, the confidence, and any warnings (excerpt from the runs in section A):

```text
2026-11-16 00:33:19,198 INFO query='something to study to on a rainy day' retrieved=['mood-focused', 'mood-sad'] profile={'favorite_genre': None, 'favorite_mood': 'focused', 'target_energy': 0.35, 'target_valence': 0.4, 'likes_acoustic': True}
2026-11-16 00:33:19,199 INFO top=['Focus Flow', 'Library Rain', 'Autumn Letters', 'Midnight Coding', 'Coffee Shop Stories'] confidence=0.53
2026-11-16 00:33:19,388 INFO query='gym workout' retrieved=['activity-workout'] profile={'favorite_genre': None, 'favorite_mood': 'intense', 'target_energy': 0.9, 'target_valence': 0.65, 'likes_acoustic': False}
2026-11-16 00:33:19,388 INFO top=['Storm Runner', 'Gym Hero', 'Concrete Crown', 'Sunrise City', 'Pulse Horizon'] confidence=0.54
2026-11-16 00:33:19,574 INFO query='qwerty zzz' retrieved=[] profile={'favorite_genre': None, 'favorite_mood': None, 'target_energy': 0.5, 'target_valence': 0.5, 'likes_acoustic': False}
2026-11-16 00:33:19,576 WARNING query='qwerty zzz' No knowledge-base match; using a neutral profile. Try naming a genre, mood or activity.
2026-11-16 00:33:19,576 WARNING query='qwerty zzz' Best match scored only 5.4/10; the catalog may not fit this request.
```

## Design Decisions

- **Retrieval drives the profile, not just the explanation.** The retrieved docs set the numbers the scorer uses. A version that printed the docs next to an unchanged answer would not really be RAG.
- **Keyword retrieval over embeddings or an LLM.** It is deterministic, offline, free, explainable and trivially testable. The cost: it misses synonyms I did not list (it failed on "asleep" until I added it), cannot handle negation ("not acoustic"), and only knows what the 25 docs cover.
- **Reuse the Module 3 scorer unchanged.** The new layer only builds a profile, so the original behavior and its tests stay valid. The cost is inheriting its biases (energy-heavy weights, exact-match mood and genre).
- **Fail soft, not hard.** Unmatched requests still return a neutral-profile list, but with 0% confidence and a warning, so the user is never silently misled and never gets a crash.
- **Whole-word matching.** Prevents false hits like "run" inside "brunch", at the price of needing explicit keyword variants.
- **Small, hand-written knowledge base and catalog.** Easy to audit, but the 18 songs mean strong requests can still get mediocre matches.

## Testing Summary

- **`python -m src.evaluate`: 12/12 checks pass, mean confidence 51%.** It runs 7 labelled requests (expected genre, energy or acousticness of the top song, determinism across repeated runs) and 5 bad inputs that must be rejected. It exits non-zero on failure, so it can gate CI.
- **`python -m pytest`: 7/7 pass.** Covers guardrails, whole-word retrieval, that retrieved docs change the profile and the final ranking, and the no-match fallback, alongside the original recommender tests.
- **What failed first:** "help me fall asleep" returned a neutral profile because "sleep" did not match "asleep". The harness caught it; adding keywords fixed it. This shows the harness works, and also that keyword coverage is the weak point.
- **What I learned:** confidence (keyword hits times top score) is a rough signal, not a calibrated probability. The 54% on the clearly good gym result looks low. The tests only check the cases I thought of, so they prove consistency, not general quality. The Module 3 adversarial findings (see appendix) still apply: conflicting preferences and a tiny catalog limit accuracy.

## Reflection

Building this showed me that most of the value in an "AI feature" is in the plumbing around it: validating input, making retrieval visible, deciding what to do when it finds nothing, and measuring behavior. Making retrieval change the profile, rather than decorate the output, forced me to be concrete about what the system actually knows. I also learned to treat a confidence number skeptically and to keep a test harness next to the model from day one. The collaboration with AI, one accepted and one revised suggestion, and the system's limitations and biases are written up in [model_card.md](model_card.md).

---

## Appendix: Original Recommender Details (Modules 1-3)

### How The System Works

#### Real-world recommenders vs. this version

Real platforms like Spotify and YouTube combine two ideas. *Collaborative filtering* learns from the behavior of millions of users (plays, skips, saves, playlist adds, watch time) to find songs that similar listeners enjoyed. *Content-based filtering* compares the attributes of a song (tempo, energy, mood, audio analysis) to what a user already likes, which also works for brand-new songs with no listening history. My simulation has no other users, so it is purely **content-based**. It prioritizes the *vibe* of a song: how close its energy and emotional tone (valence) are to what the user wants, followed by a mood match, with genre and acousticness as smaller nudges. It rewards songs for being *close* to the user's preference, not for being high or low on a feature.

#### Features used

**`Song`** (from `data/songs.csv`): `id`, `title`, `artist`, `genre`, `mood`, `energy`, `tempo_bpm`, `valence`, `danceability`, `acousticness`. The scoring rule uses `energy`, `valence`, `mood`, `genre`, and `acousticness`. Tempo and danceability are loaded but unused at first because they largely track energy.

**`UserProfile`**: `favorite_genre`, `favorite_mood`, `target_energy` (0–1), `likes_acoustic` (bool), plus a planned optional `target_valence` (0–1).

#### Algorithm Recipe (Scoring Rule for one song)

Each song earns points out of a maximum of **10.0**:

| Rule | Points | How it is computed |
|---|---|---|
| Energy closeness | up to **+3.5** | `3.5 * (1 - abs(song.energy - target_energy))` |
| Mood match | **+2.5** | `+2.5` if `song.mood == favorite_mood`, else 0 |
| Valence closeness | up to **+1.5** | `1.5 * (1 - abs(song.valence - target_valence))` |
| Genre match | **+1.5** | `+1.5` if `song.genre == favorite_genre`, else 0 |
| Acousticness closeness | up to **+1.0** | `1.0 * (1 - abs(song.acousticness - t))`, where `t = 0.8` if `likes_acoustic` else `0.2` |

- **Numeric features reward closeness, not size.** A user targeting energy 0.40 gets 3.43 points from a song at 0.35 and 1.65 from a song at 0.93. Overshooting is penalized just like undershooting.
- **Categorical features are all-or-nothing.**
- **Why mood (2.5) outweighs genre (1.5):** the common starting point is genre +2.0 and mood +1.0, but I'm deliberately flipping it. Genre is a coarse label that hides huge variety, and with 18 songs across 15 genres a genre match is rare, so a high genre weight would act as a hard filter and trap the user in one bucket. Mood is closer to what a "vibe" is and crosses genres (a chill lofi track and a relaxed jazz track can satisfy the same listener). Energy gets the most points because it was the strongest separator in the data. The genre-vs-mood weights are the first thing I'll vary in the Experiments section.
- **Left out for now:** `tempo_bpm` and `danceability` largely track energy, so including them would double-count it.

#### Taste profile used for testing

```python
user_profile = {
    "favorite_genre": "lofi",
    "favorite_mood": "chill",
    "target_energy": 0.40,
    "target_valence": 0.60,
    "likes_acoustic": True,
}
```

A hand check with this profile gives Midnight Coding (lofi, chill) about 9.8, Coffee Shop Stories (jazz, relaxed) about 5.6, and Storm Runner (rock, intense) about 3.3, so the profile cleanly separates "chill lofi" from "intense rock."

#### Ranking Rule (list of songs)

Apply the Scoring Rule to every song in the catalog, sort by score in descending order, and return the top `k`. Ties are broken by title for stable output. Each result also carries a short explanation built from the features that contributed most to its score.

**Why both rules are needed:** the Scoring Rule judges one song in isolation and answers "how well does this song fit this user?" It cannot decide what to *show*. The Ranking Rule works across the whole list: it compares scores, orders them, and cuts the list to `k`. Without scoring there is nothing to compare, and without ranking you have a pile of numbers rather than a recommendation. Separating them also lets me change one without touching the other, for example adding a diversity filter to the ranking step without altering how songs are scored.

#### Expected biases

- **Energy dominance:** energy is worth the most points (3.5 of 10), so a song with the right energy but the wrong mood and genre can still outrank a song that matches the user's mood. Energy closeness alone cannot tell a joyful high-energy song from an aggressive one, which is why valence is included.
- **Exact-match categories:** mood and genre are all-or-nothing, so "peaceful" earns nothing for a user who wants "chill" even though they are nearly the same vibe. Near-misses are punished as hard as total misses.
- **Single-taste profile:** one target per feature cannot represent a user who likes both gym and study music.
- **Tiny, uneven catalog:** lofi has 3 songs and most genres have 1, so users who prefer lofi get more good options than users who prefer, say, metal. The dataset and my own weight choices also encode my assumptions about what a "vibe" is.
- **Genre under-weighting:** the reverse risk of my choice. A listener who really cares about genre may see off-genre songs ranked above it.

---

### Sample Recommendation Output

Output of `python -m src.main` for the default pop/happy profile (`target_valence=0.80`, `likes_acoustic=False`) on the 18-song catalog:

```
Loaded songs: 18

================================================================
User profile: genre=pop, mood=happy, energy=0.8
Top 5 recommendations
================================================================

#1  Sunrise City by Neon Echo
    Score: 9.85 / 10.00
    Reasons:
      - mood match: happy (+2.5)
      - genre match: pop (+1.5)
      - energy 0.82 vs target 0.80 (+3.43)
      - valence 0.84 vs target 0.80 (+1.44)
      - acousticness 0.18 vs target 0.20 (+0.98)

#2  Rooftop Lights by Indigo Parade
    Score: 8.19 / 10.00
    Reasons:
      - mood match: happy (+2.5)
      - energy 0.76 vs target 0.80 (+3.36)
      - valence 0.81 vs target 0.80 (+1.48)
      - acousticness 0.35 vs target 0.20 (+0.85)

#3  Gym Hero by Max Pulse
    Score: 6.85 / 10.00
    Reasons:
      - genre match: pop (+1.5)
      - energy 0.93 vs target 0.80 (+3.04)
      - valence 0.77 vs target 0.80 (+1.46)
      - acousticness 0.05 vs target 0.20 (+0.85)

#4  Concrete Crown by Kid Meridian
    Score: 5.54 / 10.00
    Reasons:
      - energy 0.78 vs target 0.80 (+3.43)
      - valence 0.62 vs target 0.80 (+1.23)
      - acousticness 0.08 vs target 0.20 (+0.88)

#5  Night Drive Loop by Neon Echo
    Score: 5.34 / 10.00
    Reasons:
      - energy 0.75 vs target 0.80 (+3.32)
      - valence 0.49 vs target 0.80 (+1.03)
      - acousticness 0.22 vs target 0.20 (+0.98)

================================================================
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

### Evaluation: Profile Results

`python -m src.main` runs seven profiles defined in `src/main.py`: three realistic ones (High-Energy Pop, Chill Lofi, Deep Intense Rock) and four adversarial edge cases meant to trick the scoring logic. Full terminal output (top 5 per profile):

```
Loaded songs: 18

================================================================
PROFILE: High-Energy Pop
genre=pop, mood=happy, energy=0.8, valence=0.8, likes_acoustic=False
Top 5 recommendations
================================================================

#1  Sunrise City by Neon Echo [pop/happy]
    Score: 9.85 / 10.00
    Reasons:
      - mood match: happy (+2.5)
      - genre match: pop (+1.5)
      - energy 0.82 vs target 0.80 (+3.43)
      - valence 0.84 vs target 0.80 (+1.44)
      - acousticness 0.18 vs target 0.20 (+0.98)

#2  Rooftop Lights by Indigo Parade [indie pop/happy]
    Score: 8.19 / 10.00
    Reasons:
      - mood match: happy (+2.5)
      - energy 0.76 vs target 0.80 (+3.36)
      - valence 0.81 vs target 0.80 (+1.48)
      - acousticness 0.35 vs target 0.20 (+0.85)

#3  Gym Hero by Max Pulse [pop/intense]
    Score: 6.85 / 10.00
    Reasons:
      - genre match: pop (+1.5)
      - energy 0.93 vs target 0.80 (+3.04)
      - valence 0.77 vs target 0.80 (+1.46)
      - acousticness 0.05 vs target 0.20 (+0.85)

#4  Concrete Crown by Kid Meridian [hip hop/confident]
    Score: 5.54 / 10.00
    Reasons:
      - energy 0.78 vs target 0.80 (+3.43)
      - valence 0.62 vs target 0.80 (+1.23)
      - acousticness 0.08 vs target 0.20 (+0.88)

#5  Night Drive Loop by Neon Echo [synthwave/moody]
    Score: 5.34 / 10.00
    Reasons:
      - energy 0.75 vs target 0.80 (+3.32)
      - valence 0.49 vs target 0.80 (+1.03)
      - acousticness 0.22 vs target 0.20 (+0.98)

================================================================
PROFILE: Chill Lofi
genre=lofi, mood=chill, energy=0.4, valence=0.6, likes_acoustic=True
Top 5 recommendations
================================================================

#1  Midnight Coding by LoRoom [lofi/chill]
    Score: 9.78 / 10.00
    Reasons:
      - mood match: chill (+2.5)
      - genre match: lofi (+1.5)
      - energy 0.42 vs target 0.40 (+3.43)
      - valence 0.56 vs target 0.60 (+1.44)
      - acousticness 0.71 vs target 0.80 (+0.91)

#2  Library Rain by Paper Lanterns [lofi/chill]
    Score: 9.76 / 10.00
    Reasons:
      - mood match: chill (+2.5)
      - genre match: lofi (+1.5)
      - energy 0.35 vs target 0.40 (+3.32)
      - valence 0.60 vs target 0.60 (+1.50)
      - acousticness 0.86 vs target 0.80 (+0.94)

#3  Spacewalk Thoughts by Orbit Bloom [ambient/chill]
    Score: 7.88 / 10.00
    Reasons:
      - mood match: chill (+2.5)
      - energy 0.28 vs target 0.40 (+3.08)
      - valence 0.65 vs target 0.60 (+1.42)
      - acousticness 0.92 vs target 0.80 (+0.88)

#4  Focus Flow by LoRoom [lofi/focused]
    Score: 7.46 / 10.00
    Reasons:
      - genre match: lofi (+1.5)
      - energy 0.40 vs target 0.40 (+3.50)
      - valence 0.59 vs target 0.60 (+1.48)
      - acousticness 0.78 vs target 0.80 (+0.98)

#5  Coffee Shop Stories by Slow Stereo [jazz/relaxed]
    Score: 5.64 / 10.00
    Reasons:
      - energy 0.37 vs target 0.40 (+3.40)
      - valence 0.71 vs target 0.60 (+1.33)
      - acousticness 0.89 vs target 0.80 (+0.91)

================================================================
PROFILE: Deep Intense Rock
genre=rock, mood=intense, energy=0.92, valence=0.45, likes_acoustic=False
Top 5 recommendations
================================================================

#1  Storm Runner by Voltline [rock/intense]
    Score: 9.82 / 10.00
    Reasons:
      - mood match: intense (+2.5)
      - genre match: rock (+1.5)
      - energy 0.91 vs target 0.92 (+3.46)
      - valence 0.48 vs target 0.45 (+1.46)
      - acousticness 0.10 vs target 0.20 (+0.90)

#2  Gym Hero by Max Pulse [pop/intense]
    Score: 7.83 / 10.00
    Reasons:
      - mood match: intense (+2.5)
      - energy 0.93 vs target 0.92 (+3.46)
      - valence 0.77 vs target 0.45 (+1.02)
      - acousticness 0.05 vs target 0.20 (+0.85)

#3  Night Drive Loop by Neon Echo [synthwave/moody]
    Score: 5.32 / 10.00
    Reasons:
      - energy 0.75 vs target 0.92 (+2.90)
      - valence 0.49 vs target 0.45 (+1.44)
      - acousticness 0.22 vs target 0.20 (+0.98)

#4  Iron Cathedral by Hollow Vanguard [metal/aggressive]
    Score: 5.31 / 10.00
    Reasons:
      - energy 0.97 vs target 0.92 (+3.33)
      - valence 0.22 vs target 0.45 (+1.16)
      - acousticness 0.03 vs target 0.20 (+0.83)

#5  Concrete Crown by Kid Meridian [hip hop/confident]
    Score: 5.13 / 10.00
    Reasons:
      - energy 0.78 vs target 0.92 (+3.01)
      - valence 0.62 vs target 0.45 (+1.25)
      - acousticness 0.08 vs target 0.20 (+0.88)

================================================================
PROFILE: ADVERSARIAL: Sad but Energetic
genre=folk, mood=melancholic, energy=0.9, valence=0.2, likes_acoustic=False
Top 5 recommendations
================================================================

#1  Autumn Letters by Fern & Ash [folk/melancholic]
    Score: 7.11 / 10.00
    Reasons:
      - mood match: melancholic (+2.5)
      - genre match: folk (+1.5)
      - energy 0.30 vs target 0.90 (+1.40)
      - valence 0.25 vs target 0.20 (+1.42)
      - acousticness 0.91 vs target 0.20 (+0.29)

#2  Iron Cathedral by Hollow Vanguard [metal/aggressive]
    Score: 5.56 / 10.00
    Reasons:
      - energy 0.97 vs target 0.90 (+3.26)
      - valence 0.22 vs target 0.20 (+1.47)
      - acousticness 0.03 vs target 0.20 (+0.83)

#3  Storm Runner by Voltline [rock/intense]
    Score: 5.45 / 10.00
    Reasons:
      - energy 0.91 vs target 0.90 (+3.46)
      - valence 0.48 vs target 0.20 (+1.08)
      - acousticness 0.10 vs target 0.20 (+0.90)

#4  Night Drive Loop by Neon Echo [synthwave/moody]
    Score: 5.02 / 10.00
    Reasons:
      - energy 0.75 vs target 0.90 (+2.98)
      - valence 0.49 vs target 0.20 (+1.06)
      - acousticness 0.22 vs target 0.20 (+0.98)

#5  Gym Hero by Max Pulse [pop/intense]
    Score: 4.89 / 10.00
    Reasons:
      - energy 0.93 vs target 0.90 (+3.40)
      - valence 0.77 vs target 0.20 (+0.64)
      - acousticness 0.05 vs target 0.20 (+0.85)

================================================================
PROFILE: ADVERSARIAL: Acoustic Metalhead
genre=metal, mood=aggressive, energy=0.97, valence=0.22, likes_acoustic=True
Top 5 recommendations
================================================================

#1  Iron Cathedral by Hollow Vanguard [metal/aggressive]
    Score: 9.23 / 10.00
    Reasons:
      - mood match: aggressive (+2.5)
      - genre match: metal (+1.5)
      - energy 0.97 vs target 0.97 (+3.50)
      - valence 0.22 vs target 0.22 (+1.50)
      - acousticness 0.03 vs target 0.80 (+0.23)

#2  Storm Runner by Voltline [rock/intense]
    Score: 4.70 / 10.00
    Reasons:
      - energy 0.91 vs target 0.97 (+3.29)
      - valence 0.48 vs target 0.22 (+1.11)
      - acousticness 0.10 vs target 0.80 (+0.30)

#3  Gym Hero by Max Pulse [pop/intense]
    Score: 4.29 / 10.00
    Reasons:
      - energy 0.93 vs target 0.97 (+3.36)
      - valence 0.77 vs target 0.22 (+0.67)
      - acousticness 0.05 vs target 0.80 (+0.25)

#4  Night Drive Loop by Neon Echo [synthwave/moody]
    Score: 4.25 / 10.00
    Reasons:
      - energy 0.75 vs target 0.97 (+2.73)
      - valence 0.49 vs target 0.22 (+1.09)
      - acousticness 0.22 vs target 0.80 (+0.42)

#5  Pulse Horizon by Kairo Wave [edm/euphoric]
    Score: 4.15 / 10.00
    Reasons:
      - energy 0.95 vs target 0.97 (+3.43)
      - valence 0.90 vs target 0.22 (+0.48)
      - acousticness 0.04 vs target 0.80 (+0.24)

================================================================
PROFILE: ADVERSARIAL: Unknown Genre and Mood
genre=bossa nova, mood=dreamy, energy=0.5, valence=0.7, likes_acoustic=True
Top 5 recommendations
================================================================

#1  Dusty Porchlight by Wren Hollow [country/nostalgic]
    Score: 5.84 / 10.00
    Reasons:
      - energy 0.52 vs target 0.50 (+3.43)
      - valence 0.68 vs target 0.70 (+1.47)
      - acousticness 0.74 vs target 0.80 (+0.94)

#2  Focus Flow by LoRoom [lofi/focused]
    Score: 5.46 / 10.00
    Reasons:
      - energy 0.40 vs target 0.50 (+3.15)
      - valence 0.59 vs target 0.70 (+1.33)
      - acousticness 0.78 vs target 0.80 (+0.98)

#3  Coffee Shop Stories by Slow Stereo [jazz/relaxed]
    Score: 5.44 / 10.00
    Reasons:
      - energy 0.37 vs target 0.50 (+3.04)
      - valence 0.71 vs target 0.70 (+1.48)
      - acousticness 0.89 vs target 0.80 (+0.91)

#4  Midnight Coding by LoRoom [lofi/chill]
    Score: 5.42 / 10.00
    Reasons:
      - energy 0.42 vs target 0.50 (+3.22)
      - valence 0.56 vs target 0.70 (+1.29)
      - acousticness 0.71 vs target 0.80 (+0.91)

#5  Velvet Hours by Satin Avenue [r&b/romantic]
    Score: 5.33 / 10.00
    Reasons:
      - energy 0.55 vs target 0.50 (+3.32)
      - valence 0.72 vs target 0.70 (+1.47)
      - acousticness 0.34 vs target 0.80 (+0.54)

================================================================
PROFILE: ADVERSARIAL: Dead Center
genre=pop, mood=happy, energy=0.5, valence=0.5, likes_acoustic=False
Top 5 recommendations
================================================================

#1  Sunrise City by Neon Echo [pop/happy]
    Score: 8.35 / 10.00
    Reasons:
      - mood match: happy (+2.5)
      - genre match: pop (+1.5)
      - energy 0.82 vs target 0.50 (+2.38)
      - valence 0.84 vs target 0.50 (+0.99)
      - acousticness 0.18 vs target 0.20 (+0.98)

#2  Rooftop Lights by Indigo Parade [indie pop/happy]
    Score: 6.97 / 10.00
    Reasons:
      - mood match: happy (+2.5)
      - energy 0.76 vs target 0.50 (+2.59)
      - valence 0.81 vs target 0.50 (+1.03)
      - acousticness 0.35 vs target 0.20 (+0.85)

#3  Gym Hero by Max Pulse [pop/intense]
    Score: 5.44 / 10.00
    Reasons:
      - genre match: pop (+1.5)
      - energy 0.93 vs target 0.50 (+1.99)
      - valence 0.77 vs target 0.50 (+1.09)
      - acousticness 0.05 vs target 0.20 (+0.85)

#4  Velvet Hours by Satin Avenue [r&b/romantic]
    Score: 5.35 / 10.00
    Reasons:
      - energy 0.55 vs target 0.50 (+3.32)
      - valence 0.72 vs target 0.50 (+1.17)
      - acousticness 0.34 vs target 0.20 (+0.86)

#5  Dusty Porchlight by Wren Hollow [country/nostalgic]
    Score: 5.12 / 10.00
    Reasons:
      - energy 0.52 vs target 0.50 (+3.43)
      - valence 0.68 vs target 0.50 (+1.23)
      - acousticness 0.74 vs target 0.20 (+0.46)
```

#### What the adversarial profiles showed

- **Sad but Energetic** (folk, melancholic, energy 0.9, valence 0.2): this conflict has no good answer in the catalog, and the system reflects that. The only song matching the mood and genre, Autumn Letters (energy 0.30), still wins at 7.11 because the 4.0 points from its two label matches outweigh losing about 2.1 energy points. The next songs (Iron Cathedral, Storm Runner) are the loud, dark ones, which is a sensible compromise. The top result, though, has the opposite energy of what the user asked for.
- **Acoustic Metalhead** (metal, aggressive, energy 0.97, likes_acoustic): Iron Cathedral wins easily (9.23) even though its acousticness is 0.03 against a target of 0.8. Acousticness is worth only 1.0 point, so a preference that contradicts the user's other tastes is nearly ignored. After #1 the scores fall to about 4 to 4.7, so the list becomes a generic "loud and dark" set with the acoustic preference having no visible effect.
- **Unknown Genre and Mood** (bossa nova, dreamy): no song can earn any label points, so the ranking falls back to numeric closeness only, and the max possible score drops to 6.0. The results are reasonable (acoustic, mid-energy songs), but all five scores sit between 5.3 and 5.9, so the ordering is nearly arbitrary. The system cannot tell the user that it found no genre or mood match.
- **Dead Center** (pop, happy, energy 0.5, valence 0.5): Sunrise City still wins (8.35) despite its energy being 0.32 away from the target. The label matches (4.0 points) outweigh the energy gap, so "middle of the road" users are pulled toward songs that match their labels, not their numbers. Gym Hero (energy 0.93) lands in the top 3 on its genre match alone.

#### Other observations

- Across the realistic profiles, the top result is a near-perfect match (9.78 to 9.85), and the system separates "Chill Lofi" from "Deep Intense Rock" cleanly: no song appears in both top 5 lists.
- Gym Hero keeps showing up for pop and rock users. It earns points for the genre or mood match plus very high energy, which gives it the highest score among non-matching songs for several profiles.
- The 2.5 mood weight and 1.5 genre weight can overrule the numeric features, which is a deliberate choice but is exactly where the conflicting profiles "trick" the system.

---

### Experiments You Tried

#### Experiment 1: Weight shift (energy x2, genre x0.5)

**Change:** energy 3.5 -> 7.0 points and genre 1.5 -> 0.75 points. The maximum score rises from 10.0 to 12.75 (7.0 + 2.5 + 1.5 + 0.75 + 1.0), so scores are no longer out of 10. I added a `MAX_SCORE` constant, computed from the weights, so the printed denominator stays correct. Ranking is unaffected by the larger maximum because every song is scored on the same scale. I reverted the weights afterward, so the sample output above reflects the original recipe.

**Result: different, and only sometimes more accurate.** The top 2 songs were identical for all three realistic profiles, and the pop and lofi top 5 lists did not change at all. The changes showed up in the rock and adversarial profiles.

| Profile | Baseline | After weight shift | Better? |
|---|---|---|---|
| Deep Intense Rock | #3 Night Drive Loop, #4 Iron Cathedral, #5 Concrete Crown | Iron Cathedral rises to #3, but Pulse Horizon (EDM, euphoric, valence 0.90) enters at #4 | Mixed: metal is closer to the intent, but a happy EDM track now sneaks in on energy alone |
| Sad but Energetic | #1 Autumn Letters (sad but quiet) | #1 Storm Runner (loud, valence 0.48) | Arguably yes: it no longer recommends a quiet song to a user who asked for energy 0.9 |
| Dead Center (pop/happy, energy 0.5) | Gym Hero (energy 0.93) at #3 | Gym Hero dropped out; Velvet Hours and Dusty Porchlight (energy about 0.5) moved up | Yes: results now match the energy the user asked for |
| Unknown Genre and Mood | Dusty Porchlight, Focus Flow, Coffee Shop Stories... | Same top song, middle of the list reshuffled | Different only; the scores are still nearly tied |

**Takeaway:** doubling energy makes the system follow the numbers more closely, which helps when the labels conflict with the targets. It also lets high-energy songs with the wrong feel (Pulse Horizon for a rock fan) rise, because energy alone cannot tell an aggressive song from a euphoric one. Because I changed both weights at once, I can't say how much of the shift came from genre alone. The better fix for the "intense vs aggressive" mismatch is still partial credit for similar moods, not re-weighting.

#### Ideas still to test

- Partial credit for near-synonym moods (intense ~ aggressive, chill ~ relaxed ~ peaceful)
- Removing the mood check entirely
- Adding tempo or danceability to the score
