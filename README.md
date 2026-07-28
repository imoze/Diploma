# Diploma: Music streaming service with a recommendation system based on audio parameters

My college graduation project — a small music streaming service (internally I called it **U:V**) with a recommendation engine that finds similar tracks by how they actually *sound*, and not by what other people happened to listen to.

## Status

The project is finished. I treat it as a working prototype and a learning project — I built it to explore the technologies and the problem itself, not to ship a product. Everything works end to end: you can run it locally, walk through the whole site, stream tracks, like tracks / playlists / albums / artists, register as a listener or as an artist, upload your own tracks, build your own albums, and get recommendations. If I come back to this idea later, it will most likely be a new project built from scratch with the experience from this one — so I consider this repository done.

![Main page](https://github.com/imoze/Diploma/raw/master/main.png)

## The idea

Most popular streaming services build their recommendations on collaborative filtering — the "people who listened to this also listened to that" approach. It works well in practice, but it isn't really about the *tracks themselves*: two songs get called similar because the same people played them, not because they sound alike. So I wanted to try the other direction — a recommendation system based on the audio parameters of the tracks, so that "similar" actually means "sounds similar".

The project is made of four main modules:

1. Audio analysis
2. Database
3. API
4. Frontend

Let me walk through each one.

### Audio analysis

The purpose of this module is to extract and prepare a vector of a track's audio parameters for further use.

The heart of it is the `ExtractAudioFeatures` function (`AudioFeatures.py`). It takes a file path, loads the track via librosa, and returns a dictionary of parameters: MFCC, spectral contrast, spectral centroid, spectral bandwidth, spectral rolloff, chromagram, loudness, ZCR, BPM, key and mode. To find the key and the mode I used the Krumhansl–Schmuckler algorithm (`KrumhanslSmukler.py`) — when I was deciding which parameters to use, I wanted tonality in there, looked into how key detection is usually done, and this algorithm just felt right: it's simple, understandable, and it did the job.

The time-series features (MFCC, chromagram, and so on) are collapsed into a set of static characteristics — mean, median, variance, etc. (`StaticCharacteristics.py`). After that, `ConvertToVector.py` turns the feature dictionary into a single vector.

At this point the vector has around 700 values in it, so for simplicity and faster search it needs to be "prepared". For that I use a scaler and PCA from scikit-learn. Both have to be trained on some data first, so there is a small pipeline (`ScalerPCATrainPipeline.py`) that builds a list of feature vectors from the collection, trains the models on it, and saves them (`models/scaler.pkl`, `models/pca.pkl`, plus `model_metadata.json`). The scaler balances the values inside the vector, and then the balanced vector goes through PCA to be "compressed" from around 700 values down to around 150.

That 150 isn't a magic number, by the way — I train PCA to keep 95% of the variance, so the resulting size is just however many components that takes on my data. On a small test set it came out around 70; on the full collection it landed at around 150.

Once the models are trained, analysing a new track is a separate function (`NewTrackAnalysis.py`) that takes the pre-trained scaler and PCA and a track, and returns its final vector. This is what the API calls whenever a new track is uploaded.

### Database

The database is PostgreSQL with the **pgvector** extension, and this is where the whole approach comes together.

Most of the schema is a normal relational model: `users`, `track`, `artist`, `album`, `playlist`, their association tables (playlist ↔ tracks, album ↔ tracks, artist ↔ tracks / albums / members, favorites with ordering), listening `history`, and a set of role tables — `member` for artist accounts, `admin` with `role` / `privilege`, and an audit `log`. Primary keys are UUIDs, and things like history source details and audit diffs are stored as JSONB.

The interesting part is that each row in `track` has a `feature_vector` column of type `vector(150)` — a pgvector column sitting right next to the ordinary relational data. So a track's audio embedding lives in the same table as its name, duration and play count, and similarity search happens inside the same database as everything else, with no separate storage to keep in sync.

### API

The API is built on **FastAPI** and split by resource: `tracks`, `auth`, `users`, `playlists`, `artists`, `albums`. Authentication is JWT (via python-jose) with Argon2 password hashing. Data in and out is validated with Pydantic schemas.

The most important routes are the track ones:

| Method | Path | What it does |
|--------|------|--------------|
| GET | `/api/tracks/` | List tracks, with optional search |
| POST | `/api/tracks/` | Upload a new track (mp3) |
| GET | `/api/tracks/{id}` | Get a single track |
| PATCH | `/api/tracks/{id}` | Update track metadata |
| DELETE | `/api/tracks/{id}` | Delete a track |
| GET | `/api/tracks/{id}/stream` | Stream the audio file |
| GET | `/api/tracks/{id}/similar` | Find similar tracks (recommendations) |
| POST · DELETE | `/api/tracks/{id}/like` | Add / remove from favorites |

Upload is where the analysis hooks in. When an artist uploads a track, the row is written to the database right away with an empty vector and the response returns immediately — the heavy work doesn't block it. In parallel, a background task loads the pre-trained scaler and PCA, runs the analysis, and fills in the track's duration and `feature_vector`.

The `/similar` endpoint is the payoff: it takes the track's vector and runs a pgvector cosine-distance search using the `<=>` operator — `1 - (feature_vector <=> :query) AS similarity` — orders the results from closest to farthest, and returns the nearest tracks as a ranked list with a similarity score.

### Frontend

The frontend is plain HTML, CSS and JavaScript, no framework. The pages cover the whole service: `index`, `search`, `artist`, `album`, `playlist`, `track`, `profile`, `login`, `register`, `my-wave` (the recommendations page) and `admin`. There's a custom streaming player (`player.js`), a small wave animation for the player, and thin `api.js` / `auth.js` layers talking to the API.

I'll be honest here: the frontend is the part I enjoy least, so it was mostly "vibe-coded" on top of basic HTML/CSS/JS. It does its job — you can see and use everything the backend offers — but it's the most obvious place the project could be improved.

![Artist page](https://github.com/imoze/Diploma/raw/master/artist.png)

![My wave page](https://github.com/imoze/Diploma/raw/master/wave.png)2

## How a recommendation is made, end to end

The tracks that already sit in the database were analysed during training, so their vectors are ready. For a new track the flow is:

1. An artist uploads an mp3 on their profile page and gives it a name and some metadata.
2. The track is saved to the database immediately with an empty vector, so the upload returns fast.
3. In parallel, a background task builds the ~700-value feature vector, loads the pre-trained scaler and PCA, reduces it to ~150 dimensions, and stores the result in the pgvector column.
4. After that, opening the track and pressing "find similar" runs a cosine-distance search in pgvector and returns the nearest tracks as a ranked list.

## Stack

**Major**

- PostgreSQL + pgvector
- Librosa
- FastAPI
- SQLAlchemy
- Pydantic

**Also used**

- NumPy
- SciPy
- scikit-learn
- Joblib
- Argon2
- python-jose

## Dataset

The audio itself is not in this repository. The scaler and PCA were trained on around 2300 tracks I collected from my own music library — favorite artists, organized by genre → artist → album. Since this is a non-commercial, educational project and I'm not distributing the music, I keep the audio out of the repo; only the trained models under `models/` are needed to analyse new uploads.

## Limitations & where it could go

The most basic part is the frontend, for the reason above. Beyond that, this is a prototype — it fully did what I wanted it to do, and taking it further really only makes sense as a commercial product. If it went that way, the natural next steps would be:

- Moving the track vectors into a dedicated **vector database** for faster search and richer querying — not just plain cosine similarity. (In a real product you'd keep a normal relational DB for users, tracks and playlists, and store the vector representations in a specialized vector store.)
- Improving and expanding the **analysis algorithm** — I don't consider it perfect.
- Adding other **recommendation algorithms**, including classic collaborative filtering alongside the audio-based one.
- Storing several **embeddings per track**, so recommendations could be steered — e.g. "find a similar melody" vs. "find a similar set of instruments".
- An **admin panel** and proper roles, so the site can be administered through the UI instead of by hand in the database.
- More **statistics and dashboards**, especially for artists.

A dedicated vector DB is the clearest "next step", but for the scale and goals of this project it simply wasn't necessary — pgvector already covers everything I needed (vector storage, vector search, vector indexes) without adding a second database to the project.

## Running

The project runs locally against PostgreSQL with the pgvector extension. A proper setup guide — dependencies, environment variables, database initialization — isn't written yet; I'll add it later.

## Contact

- Email: `game-f-90@mail.ru`
- Telegram: `@Imoze`
