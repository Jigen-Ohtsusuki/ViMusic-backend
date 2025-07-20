from fastapi import FastAPI, HTTPException, Query
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import os
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    raise Exception("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set.")

credentials = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=credentials)

app = FastAPI()

@app.get("/playlist")
def get_playlist_tracks(playlist_id: str = Query(..., description="Spotify playlist ID")):
    try:
        results = sp.playlist_tracks(playlist_id)
        all_tracks = []

        while results:
            for item in results['items']:
                track = item['track']
                if track is None:
                    continue
                title = track['name']
                artists = ", ".join([artist['name'] for artist in track['artists']])
                all_tracks.append({
                    "title": title,
                    "artist": artists
                })

            results = sp.next(results) if results['next'] else None

        return {"tracks": all_tracks}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/album")
def get_album_tracks(album_id: str):
    try:
        results = sp.album_tracks(album_id)
        tracks = []

        for item in results["items"]:
            track_name = item["name"]
            artists = ", ".join([artist["name"] for artist in item["artists"]])
            tracks.append({"title": track_name, "artist": artists})

        return {"tracks": tracks}

    except spotipy.SpotifyException as e:
        raise HTTPException(status_code=500, detail=str(e))
