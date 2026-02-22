"""
Centralisation des chemins du projet (données, config).
Tous les chemins sont résolus par rapport à la racine du projet.
"""
from pathlib import Path

# Racine du projet (parent de src/ lorsque ce module est dans src/spotifyapp/)
# __file__ = .../src/spotifyapp/paths.py -> parent.parent.parent = racine projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Dossiers principaux
DIR_DATA = PROJECT_ROOT / "data"
DIR_CONFIG = PROJECT_ROOT / "config"
DIR_GENRES = DIR_DATA / "genres"


def path_weights(class_code: str, bucket_key: str) -> Path:
    """Chemin du fichier de poids du modèle pour une classe et un bucket."""
    name = f"weights_{class_code}_{bucket_key.replace('.', '_')}.json"
    return DIR_DATA / name


def path_last_update() -> Path:
    """Chemin du fichier de dernière mise à jour des playlists."""
    return DIR_DATA / "last_update.json"


def path_genre_cache() -> Path:
    """Chemin du fichier de cache des genres."""
    return DIR_DATA / "genre_cache.json"


def path_id_client() -> Path:
    """Chemin du fichier des identifiants Spotify (CLIENT_ID, etc.)."""
    return DIR_CONFIG / "ID_client.txt"
