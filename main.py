from fastapi import FastAPI, HTTPException, Query
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    logger.error("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")
    raise Exception("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set.")

logger.info("Initializing Spotify client with client_id: %s", client_id)
credentials = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=credentials)

app = FastAPI()

@app.get("/playlist")
def get_playlist_tracks(playlist_id: str = Query(..., description="Spotify playlist ID")):
    try:
        logger.info("Fetching playlist tracks for playlist_id: %s", playlist_id)
        results = sp.playlist_tracks(playlist_id)
        logger.info("Received initial playlist response: %s items", len(results['items']))
        all_tracks = []

        while results:
            logger.info("Processing page with %s items, next: %s", len(results['items']), results['next'])
            for item in results['items']:
                track = item['track']
                if track is None:
                    logger.warning("Skipping null track in playlist")
                    continue
                title = track['name']
                artists = ", ".join([artist['name'] for artist in track['artists']])
                logger.debug("Processing track: %s by %s", title, artists)
                all_tracks.append({
                    "title": title,
                    "artist": artists
                })

            if results['next']:
                logger.info("Fetching next page of tracks")
                results = sp.next(results)
                logger.info("Received next page response: %s items", len(results['items']) if results else 0)
            else:
                logger.info("No more pages to fetch")
                results = None

        logger.info("Total tracks fetched: %s", len(all_tracks))
        return {"tracks": all_tracks}

    except Exception as e:
        logger.error("Error fetching playlist tracks: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/album")
def get_album_tracks(album_id: str):
    try:
        logger.info("Fetching album tracks for album_id: %s", album_id)
        results = sp.album_tracks(album_id)
        logger.info("Received album response: %s items", len(results['items']))
        tracks = []

        for item in results["items"]:
            track_name = item["name"]
            artists = ", ".join([artist["name"] for artist in item["artists"]])
            logger.debug("Processing album track: %s by %s", track_name, artists)
            tracks.append({"title": track_name, "artist": artists})

        logger.info("Total album tracks fetched: %s", len(tracks))
        return {"tracks": tracks}

    except spotipy.SpotifyException as e:
        logger.error("Spotify API error for album: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
