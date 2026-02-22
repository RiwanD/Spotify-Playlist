import sys
import time
from pathlib import Path
from collections import defaultdict

# Permettre l'import du package spotifyapp (depuis la racine du projet)
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from spotifyapp.credentials import sp
from spotifyapp.music_genre import create_playlists_by_class, load_class_genres
from spotifyapp.analyze_auto_playlists import analyze_auto_playlists
from spotifyapp.find_auto_playlists import find_all_playlists
from spotifyapp.list_playlists import list_all_playlists
from spotifyapp.check_auto_created import check_auto_playlists
from spotifyapp.delete_playlist import delete_playlists
from spotifyapp.update_playlists import update_playlists_main


def get_liked_tracks():
    """Récupère toutes les chansons likées de l'utilisateur."""
    print("\n[*] Recuperation des chansons likees...")
    liked_tracks = []
    results = sp.current_user_saved_tracks(limit=50)
    while results:
        for item in results["items"]:
            track = item["track"]
            liked_tracks.append(track)
        results = sp.next(results) if results["next"] else None
    
    print(f"[*] Nombre de chansons likees recuperees : {len(liked_tracks)}")
    return liked_tracks


def analyze_genres(liked_tracks, use_cache=True, force_refresh=False):
    """
    Analyse les genres des artistes pour chaque chanson likée.
    
    Args:
        liked_tracks: Liste des titres likés
        use_cache: Si True, utilise le cache pour éviter les appels API répétés
        force_refresh: Si True, force la mise à jour depuis l'API même si en cache
    
    Returns:
        Tuple (genre_dict, track_genres_dict)
    """
    print("\n[*] Analyse des genres des artistes...")
    
    if use_cache:
        from spotifyapp.genre_cache import get_cache
        cache = get_cache()
        
        # Afficher les stats du cache
        stats = cache.get_cache_stats()
        print(f"[*] Cache: {stats['tracks_cached']} titres, {stats['artists_cached']} artistes en cache")
        
        # Récupérer les URIs des titres
        track_uris = [track["uri"] for track in liked_tracks]
        
        # Analyser avec le cache
        def progress_callback(idx, total):
            print(f"  -> {idx}/{total} pistes analysees...")
        
        track_genres_dict = cache.analyze_tracks_genres(
            track_uris, 
            force_refresh=force_refresh,
            progress_callback=progress_callback
        )
    else:
        # Méthode originale sans cache
        track_genres_dict = {}
        artist_cache = {}
        for idx, track in enumerate(liked_tracks, 1):
            artist_id = track["artists"][0]["id"]
            if artist_id not in artist_cache:
                artist_cache[artist_id] = sp.artist(artist_id)
            artist_info = artist_cache[artist_id]
            time.sleep(0.1)  # Pour eviter de trop solliciter l'API
            genres = artist_info.get("genres", ["Unknown"])
            track_genres_dict[track["uri"]] = genres
            
            if idx % 50 == 0:
                print(f"  -> {idx}/{len(liked_tracks)} pistes analysees...")
    
    # Construire le genre_dict à partir de track_genres_dict
    genre_dict = defaultdict(list)
    for track_uri, genres in track_genres_dict.items():
        for genre in genres:
            genre_dict[genre].append(track_uri)
    
    print(f"[*] {len(genre_dict)} genres differents trouves dans les chansons likees\n")
    return genre_dict, track_genres_dict


def show_help():
    """Affiche l'aide avec toutes les options disponibles."""
    print("=" * 80)
    print("SPOTIFY APP - MENU PRINCIPAL")
    print("=" * 80)
    print("\nOptions disponibles :")
    print("  (aucune option)     : Créer les playlists par classe (nomenclature française)")
    print("  --analyze           : Analyser les playlists contenant '(auto)'")
    print("  --find              : Trouver les playlists suspectes (auto, generated, etc.)")
    print("  --list              : Lister toutes vos playlists")
    print("  --check             : Vérifier les playlists créées automatiquement")
    print("  --delete            : Supprimer des playlists (utilisez --auto pour cibler les '(auto)')")
    print("  --update            : Mettre à jour les playlists avec les nouveaux titres likés")
    print("  --confirm           : Confirmer les actions (création/suppression)")
    print("  --scoring           : Utiliser le système de scoring pondéré (nécessite entraînement)")
    print("  --no-cache          : Désactiver l'utilisation du cache des genres")
    print("  --refresh-cache     : Forcer la mise à jour du cache depuis l'API")
    print("  --cache-stats       : Afficher les statistiques du cache")
    print("  --clear-cache       : Vider le cache des genres")
    print("\nExemples :")
    print("  python main.py                    # Dry-run : créer les playlists par classe")
    print("  python main.py --confirm           # Créer réellement les playlists par classe")
    print("  python main.py --analyze           # Analyser les playlists auto")
    print("  python main.py --find              # Trouver les playlists suspectes")
    print("  python main.py --list              # Lister toutes les playlists")
    print("  python main.py --check             # Vérifier les playlists auto")
    print("  python main.py --delete --auto     # Dry-run : supprimer les playlists '(auto)'")
    print("  python main.py --delete --auto --confirm  # Supprimer réellement les playlists '(auto)'")
    print("  python main.py --update            # Dry-run : mettre à jour les playlists")
    print("  python main.py --update --confirm  # Mettre à jour réellement les playlists")
    print("=" * 80)


def main():
    """Fonction principale qui route vers les différentes fonctionnalités."""
    # --- Test : récupérer ton profil ---
    me = sp.current_user()
    confirm = ("--confirm" in sys.argv)
    
    print("[*] Connexion reussie")
    print(f"[*] Utilisateur : {me.get('display_name')} | ID Spotify : {me['id']}")
    
    # Détection des options
    if "--help" in sys.argv or "-h" in sys.argv:
        show_help()
        return
    
    if "--analyze" in sys.argv:
        print("\n[*] Mode : Analyse des playlists auto\n")
        analyze_auto_playlists()
        return
    
    if "--find" in sys.argv:
        print("\n[*] Mode : Recherche de playlists suspectes\n")
        find_all_playlists()
        return
    
    if "--list" in sys.argv:
        print("\n[*] Mode : Liste de toutes les playlists\n")
        list_all_playlists()
        return
    
    if "--check" in sys.argv:
        print("\n[*] Mode : Vérification des playlists auto\n")
        check_auto_playlists()
        return
    
    if "--delete" in sys.argv:
        print("\n[*] Mode : Suppression de playlists\n")
        auto_mode = ("--auto" in sys.argv)
        delete_playlists(confirm=confirm, auto_mode=auto_mode)
        return
    
    if "--update" in sys.argv:
        print("\n[*] Mode : Mise à jour des playlists\n")
        use_cache = ("--no-cache" not in sys.argv)
        force_refresh = ("--refresh-cache" in sys.argv)
        update_playlists_main(confirm=confirm, use_cache=use_cache, force_refresh=force_refresh)
        return
    
    if "--cache-stats" in sys.argv:
        print("\n[*] Statistiques du cache\n")
        from spotifyapp.genre_cache import get_cache
        cache = get_cache()
        stats = cache.get_cache_stats()
        print(f"Fichier de cache: {stats['cache_file']}")
        print(f"Titres en cache: {stats['tracks_cached']}")
        print(f"Artistes en cache: {stats['artists_cached']}")
        if stats['created_at']:
            from datetime import datetime
            created = datetime.fromtimestamp(stats['created_at'])
            updated = datetime.fromtimestamp(stats['last_updated'])
            print(f"Créé le: {created.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Dernière mise à jour: {updated.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    if "--clear-cache" in sys.argv:
        print("\n[*] Vidage du cache\n")
        from spotifyapp.genre_cache import get_cache
        cache = get_cache()
        cache.clear_cache(confirm=True)
        return
    
    # Par défaut : créer les playlists par classe
    print("\n[*] Mode : Création de playlists par classe (nomenclature française)\n")
    use_scoring = ("--scoring" in sys.argv)
    use_cache = ("--no-cache" not in sys.argv)
    force_refresh = ("--refresh-cache" in sys.argv)
    
    if use_scoring:
        print("[*] Mode scoring pondere active\n")
    if not use_cache:
        print("[*] Cache des genres desactive\n")
    if force_refresh:
        print("[*] Mise a jour forcee du cache depuis l'API\n")
    
    # Créer une fonction wrapper pour analyze_genres avec les paramètres de cache
    def analyze_genres_with_cache(liked_tracks):
        return analyze_genres(liked_tracks, use_cache=use_cache, force_refresh=force_refresh)
    
    create_playlists_by_class(
        confirm=confirm, 
        get_liked_tracks_func=get_liked_tracks, 
        analyze_genres_func=analyze_genres_with_cache,
        use_scoring=use_scoring
    )


if __name__ == "__main__":
    main()
