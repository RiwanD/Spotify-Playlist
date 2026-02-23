"""
Cache des playlists (auto) et sélection "staged" pour mise à jour partielle (mode git).

- playlist_cache.json : liste des playlists (auto) connues (nom -> id, etc.)
- staged_playlists.json : noms des playlists à mettre à jour lors du prochain --update
"""
import json
from pathlib import Path

from .credentials import sp
from .paths import path_playlist_cache, path_staged_playlists


def load_playlist_cache():
    """
    Charge le cache des playlists depuis le fichier.

    Returns:
        dict: {playlist_name: {"id": ..., "tracks_count": ...}} ou {} si absent
    """
    p = path_playlist_cache()
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_playlist_cache(cache):
    """Sauvegarde le cache des playlists."""
    p = path_playlist_cache()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def refresh_playlist_cache(suffix="(auto)"):
    """
    Récupère toutes les playlists de l'utilisateur dont le nom se termine par suffix,
    les enregistre dans le cache et retourne le cache.

    Args:
        suffix: filtre sur le nom (par défaut "(auto)")

    Returns:
        dict: cache {playlist_name: {"id": ..., "tracks_count": ...}}
    """
    playlists = []
    results = sp.current_user_playlists(limit=50)
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results.get("next") else None

    cache = {}
    for pl in playlists:
        name = pl.get("name") or ""
        if not name.endswith(suffix):
            continue
        cache[name] = {
            "id": pl.get("id"),
            "tracks_count": pl.get("tracks", {}).get("total", 0),
        }
    save_playlist_cache(cache)
    return cache


def load_staged_playlists():
    """
    Charge la liste des noms de playlists "staged" (à mettre à jour).

    Returns:
        list: noms de playlists, ou [] si fichier absent/vide
    """
    p = path_staged_playlists()
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            names = data.get("playlists", data if isinstance(data, list) else [])
            return names if isinstance(names, list) else []
    except Exception:
        return []


def save_staged_playlists(names):
    """Sauvegarde la liste des playlists staged."""
    p = path_staged_playlists()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"playlists": names}, f, indent=2, ensure_ascii=False)


def clear_staged_playlists():
    """Vide la liste des playlists staged."""
    save_staged_playlists([])
