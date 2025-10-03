import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import defaultdict

# --- Configuration ---
CLIENT_ID = "54d446713a8d4aea930b4fb53a22a7c3"
CLIENT_SECRET = "38379bab42714231b7ce0ce0680bef9c"
REDIRECT_URI = "http://localhost:8888/callback"

SCOPE = "user-library-read playlist-modify-public playlist-modify-private"

# --- Authentification ---
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

# --- Récupère ton user_id ---
user_id = sp.current_user()["id"]

# --- Récupère toutes tes chansons likées ---
liked_tracks = []
results = sp.current_user_saved_tracks(limit=50)
while results:
    for item in results["items"]:
        track = item["track"]
        liked_tracks.append(track)
    results = sp.next(results) if results["next"] else None

print(f"Nombre de chansons likées récupérées : {len(liked_tracks)}")

# --- Classement par genre ---
genre_dict = defaultdict(list)

for track in liked_tracks:
    artist_id = track["artists"][0]["id"]
    artist_info = sp.artist(artist_id)
    genres = artist_info.get("genres", ["Unknown"])
    
    # Ajoute la chanson à tous les genres associés
    for genre in genres:
        genre_dict[genre].append(track["uri"])

# --- Création des playlists par genre ---
for genre, uris in genre_dict.items():
    # Limiter à 1000 morceaux par playlist (API restriction)
    uris = uris[:1000]
    
    # Crée la playlist
    playlist = sp.user_playlist_create(
        user=user_id,
        name=f"{genre.title()} Mix (auto)",
        public=False,
        description=f"Playlist auto-générée par genre : {genre}"
    )
    
    # Ajoute les morceaux
    sp.playlist_add_items(playlist["id"], uris)
    print(f"✅ Playlist créée : {playlist['name']} ({len(uris)} titres)")
