"""
Module de cache pour les genres musicaux.

Ce module permet de sauvegarder et charger les genres des titres depuis un fichier
pour éviter de refaire les appels API Spotify à chaque exécution.
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from credentials import sp


CACHE_FILE = "genre_cache.json"
CACHE_VERSION = 1  # Version du format de cache (pour migrations futures)


class GenreCache:
    """Gère le cache des genres musicaux."""
    
    def __init__(self, cache_file: str = CACHE_FILE):
        """
        Initialise le cache.
        
        Args:
            cache_file: Chemin du fichier de cache
        """
        self.cache_file = Path(cache_file)
        self.cache_data = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Charge le cache depuis le fichier."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Vérifier la version du cache
                    if data.get("version") == CACHE_VERSION:
                        return data
                    else:
                        print(f"[!] Version de cache incompatible, creation d'un nouveau cache")
                        return self._create_empty_cache()
            except Exception as e:
                print(f"[!] Erreur lors du chargement du cache: {e}")
                return self._create_empty_cache()
        else:
            return self._create_empty_cache()
    
    def _create_empty_cache(self) -> Dict:
        """Crée une structure de cache vide."""
        return {
            "version": CACHE_VERSION,
            "created_at": time.time(),
            "last_updated": time.time(),
            "tracks": {},  # {track_uri: {genres: [...], artist_id: "...", updated_at: timestamp}}
            "artists": {}  # {artist_id: {genres: [...], updated_at: timestamp}}
        }
    
    def _save_cache(self):
        """Sauvegarde le cache dans le fichier."""
        try:
            self.cache_data["last_updated"] = time.time()
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[!] Erreur lors de la sauvegarde du cache: {e}")
    
    def get_track_genres(self, track_uri: str, force_refresh: bool = False) -> Optional[List[str]]:
        """
        Récupère les genres d'un titre depuis le cache ou l'API.
        
        Args:
            track_uri: URI du titre
            force_refresh: Si True, force la mise à jour depuis l'API
        
        Returns:
            Liste des genres ou None si le titre n'existe pas
        """
        # Vérifier le cache
        if not force_refresh and track_uri in self.cache_data["tracks"]:
            return self.cache_data["tracks"][track_uri]["genres"]
        
        # Récupérer depuis l'API
        try:
            track_id = track_uri.split(":")[-1]
            track = sp.track(track_id)
            
            if not track["artists"]:
                return None
            
            artist_id = track["artists"][0]["id"]
            
            # Récupérer les genres de l'artiste (depuis le cache si disponible)
            genres = self.get_artist_genres(artist_id, force_refresh=force_refresh)
            
            # Mettre en cache
            self.cache_data["tracks"][track_uri] = {
                "genres": genres,
                "artist_id": artist_id,
                "updated_at": time.time()
            }
            
            return genres
        except Exception as e:
            print(f"[!] Erreur lors de la recuperation des genres pour {track_uri}: {e}")
            return None
    
    def get_artist_genres(self, artist_id: str, force_refresh: bool = False) -> List[str]:
        """
        Récupère les genres d'un artiste depuis le cache ou l'API.
        
        Args:
            artist_id: ID de l'artiste Spotify
            force_refresh: Si True, force la mise à jour depuis l'API
        
        Returns:
            Liste des genres
        """
        # Vérifier le cache
        if not force_refresh and artist_id in self.cache_data["artists"]:
            return self.cache_data["artists"][artist_id]["genres"]
        
        # Récupérer depuis l'API
        try:
            artist_info = sp.artist(artist_id)
            genres = artist_info.get("genres", ["Unknown"])
            
            # Mettre en cache
            self.cache_data["artists"][artist_id] = {
                "genres": genres,
                "updated_at": time.time()
            }
            
            return genres
        except Exception as e:
            print(f"[!] Erreur lors de la recuperation des genres pour l'artiste {artist_id}: {e}")
            return ["Unknown"]
    
    def analyze_tracks_genres(
        self, 
        track_uris: List[str], 
        force_refresh: bool = False,
        progress_callback: Optional[callable] = None,
        save_every_n: int = 50
    ) -> Dict[str, List[str]]:
        """
        Analyse les genres de plusieurs titres en utilisant le cache.
        
        Le cache est sauvegardé après chaque tranche de `save_every_n` titres
        récupérés depuis l'API, afin de conserver la progression en cas d'arrêt
        (rate limit, interruption, etc.).
        
        Args:
            track_uris: Liste des URIs des titres
            force_refresh: Si True, force la mise à jour depuis l'API
            progress_callback: Fonction appelée pour afficher la progression (idx, total)
            save_every_n: Sauvegarder le cache sur disque après chaque N titres récupérés via l'API (défaut: 50)
        
        Returns:
            Dictionnaire {track_uri: [genres]}
        """
        track_genres_dict = {}
        total = len(track_uris)
        cached_count = 0
        api_count = 0
        
        for idx, track_uri in enumerate(track_uris, 1):
            # Vérifier le cache d'abord
            if not force_refresh and track_uri in self.cache_data["tracks"]:
                track_genres_dict[track_uri] = self.cache_data["tracks"][track_uri]["genres"]
                cached_count += 1
            else:
                # Récupérer depuis l'API
                genres = self.get_track_genres(track_uri, force_refresh=force_refresh)
                if genres:
                    track_genres_dict[track_uri] = genres
                    api_count += 1
                    
                    # Sauvegarde incrémentale : après chaque tranche de titres récupérés via l'API
                    if save_every_n > 0 and (api_count == 1 or api_count % save_every_n == 0):
                        self._save_cache()
                
                # Petite pause pour éviter de surcharger l'API
                if api_count > 0 and api_count % 10 == 0:
                    time.sleep(0.1)
            
            # Callback de progression
            if progress_callback and idx % 50 == 0:
                progress_callback(idx, total)
        
        # Sauvegarder une dernière fois s'il reste des entrées non sauvegardées
        if api_count > 0:
            self._save_cache()
            print(f"[*] Cache mis a jour: {cached_count} depuis le cache, {api_count} depuis l'API")
        
        return track_genres_dict
    
    def get_cache_stats(self) -> Dict:
        """Retourne des statistiques sur le cache."""
        tracks_count = len(self.cache_data["tracks"])
        artists_count = len(self.cache_data["artists"])
        
        created_at = self.cache_data.get("created_at", 0)
        last_updated = self.cache_data.get("last_updated", 0)
        
        return {
            "tracks_cached": tracks_count,
            "artists_cached": artists_count,
            "created_at": created_at,
            "last_updated": last_updated,
            "cache_file": str(self.cache_file)
        }
    
    def clear_cache(self, confirm: bool = False):
        """
        Vide le cache.
        
        Args:
            confirm: Si True, vide réellement le cache
        """
        if not confirm:
            print("[!] Pour vider le cache, utilisez clear_cache(confirm=True)")
            return
        
        self.cache_data = self._create_empty_cache()
        self._save_cache()
        print("[+] Cache vide")
    
    def remove_track(self, track_uri: str):
        """Supprime un titre du cache."""
        if track_uri in self.cache_data["tracks"]:
            del self.cache_data["tracks"][track_uri]
            self._save_cache()
    
    def remove_artist(self, artist_id: str):
        """Supprime un artiste du cache."""
        if artist_id in self.cache_data["artists"]:
            del self.cache_data["artists"][artist_id]
            # Supprimer aussi les références dans les titres
            for track_uri, track_data in list(self.cache_data["tracks"].items()):
                if track_data.get("artist_id") == artist_id:
                    del self.cache_data["tracks"][track_uri]
            self._save_cache()


# Instance globale du cache
_cache_instance = None


def get_cache() -> GenreCache:
    """Retourne l'instance globale du cache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = GenreCache()
    return _cache_instance
