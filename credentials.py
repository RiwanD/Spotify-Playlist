import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- Fonction pour lire le fichier de config ---
def read_config(filename="ID_client.txt"):
    config = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            # Nettoyer les lignes
            line = line.strip()
            if line and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                config[key] = value
    return config

# --- Charger les infos du fichier ---
config = read_config("ID_client.txt")

CLIENT_ID = config.get("CLIENT_ID")
CLIENT_SECRET = config.get("CLIENT_SECRET")
REDIRECT_URI = config.get("REDIRECT_URI")

# --- Vérification ---
print("Client ID:", CLIENT_ID)
print("Redirect URI:", REDIRECT_URI)

# --- Authentification ---
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-library-read playlist-read-private playlist-modify-public playlist-modify-private"
))