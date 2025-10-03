import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import defaultdict
from credentials import sp
import time

# --- Récupère ton user_id ---
user_id = sp.current_user()["id"]

# --- Test : récupérer ton profil ---
me = sp.current_user()
print("Connexion réussie ✅")
print("Utilisateur :", me["display_name"], "| ID Spotify :", me["id"])

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
artist_cache = {}
for track in liked_tracks:
    artist_id = track["artists"][0]["id"]
    if artist_id not in artist_cache:
        artist_cache[artist_id] = sp.artist(artist_id)
    artist_info = artist_cache[artist_id]
    time.sleep(0.1)  # Pour éviter de trop solliciter l'API
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
