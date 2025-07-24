from fastapi import FastAPI, HTTPException, Query
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import os
from dotenv import load_dotenv
import logging
import threading
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env
load_dotenv()
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    logger.error("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")
    raise Exception("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")

# Setup Spotify client
logger.info("Initializing Spotify client with client_id: %s", client_id)
credentials = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=credentials)

# Initialize FastAPI app
app = FastAPI()

# 1 call/sec throttle control
spotify_lock = threading.Lock()
last_call_time = 0

def rate_limited_call(func, *args, **kwargs):
    global last_call_time
    with spotify_lock:
        now = time.time()
        elapsed = now - last_call_time
        if elapsed < 1:
            sleep_time = 1 - elapsed
            logger.debug("Sleeping %.2f seconds to throttle", sleep_time)
            time.sleep(sleep_time)

        result = func(*args, **kwargs)
        last_call_time = time.time()
        return result

# --- Playlist Endpoint ---
@app.get("/playlist")
def get_playlist_tracks(playlist_id: str = Query(..., description="Spotify playlist ID")):
    try:
        logger.info("Fetching playlist: %s", playlist_id)
        results = rate_limited_call(sp.playlist_tracks, playlist_id, offset=0, limit=100)
        all_tracks = []

        while results:
            logger.info("Processing %d tracks", len(results['items']))
            for item in results['items']:
                track = item.get('track')
                if not track:
                    logger.warning("Skipping null track")
                    continue

                title = track['name']
                artists = ", ".join([a['name'] for a in track['artists']])
                all_tracks.append({"title": title, "artist": artists})

            if results['next']:
                results = rate_limited_call(sp.next, results)
            else:
                break

        logger.info("Fetched %d total tracks", len(all_tracks))
        return {"tracks": all_tracks}

    except spotipy.SpotifyException as e:
        if e.http_status == 429:
            retry_after = e.http_response.headers.get("Retry-After", "1")
            logger.error("Rate limit hit, Retry-After: %s seconds", retry_after)
            raise HTTPException(status_code=429, detail=f"Rate limit hit. Retry after {retry_after} seconds.")
        elif e.http_status == 404:
            logger.error("Playlist not found: %s", e)
            raise HTTPException(status_code=404, detail="Playlist not found")
        else:
            logger.error("Spotify API error: %s", e)
            raise HTTPException(status_code=500, detail="Spotify API error")

    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Unexpected error")

# --- Album Endpoint ---
@app.get("/album")
def get_album_tracks(album_id: str = Query(..., description="Spotify album ID")):
    try:
        logger.info("Fetching album: %s", album_id)
        results = rate_limited_call(sp.album_tracks, album_id, limit=50)
        tracks = []

        for item in results["items"]:
            title = item["name"]
            artists = ", ".join([a["name"] for a in item["artists"]])
            tracks.append({"title": title, "artist": artists})

        logger.info("Fetched %d album tracks", len(tracks))
        return {"tracks": tracks}

    except spotipy.SpotifyException as e:
        if e.http_status == 429:
            retry_after = e.http_response.headers.get("Retry-After", "1")
            logger.error("Rate limit hit, Retry-After: %s seconds", retry_after)
            raise HTTPException(status_code=429, detail=f"Rate limit hit. Retry after {retry_after} seconds.")
        elif e.http_status == 404:
            logger.error("Album not found: %s", e)
            raise HTTPException(status_code=404, detail="Album not found")
        else:
            logger.error("Spotify API error: %s", e)
            raise HTTPException(status_code=500, detail="Spotify API error")

    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Unexpected error")
