import sys
import time
from collections import defaultdict
from credentials import sp
from music_genre import create_playlists_by_class, load_class_genres
from analyze_auto_playlists import analyze_auto_playlists
from find_auto_playlists import find_all_playlists
from list_playlists import list_all_playlists
from check_auto_created import check_auto_playlists
from delete_playlist import delete_playlists
from update_playlists import main as update_playlists_main


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


def analyze_genres(liked_tracks):
    """Analyse les genres des artistes pour chaque chanson likée."""
    print("\n[*] Analyse des genres des artistes...")
    genre_dict = defaultdict(list)
    artist_cache = {}
    for idx, track in enumerate(liked_tracks, 1):
        artist_id = track["artists"][0]["id"]
        if artist_id not in artist_cache:
            artist_cache[artist_id] = sp.artist(artist_id)
        artist_info = artist_cache[artist_id]
        time.sleep(0.1)  # Pour eviter de trop solliciter l'API
        genres = artist_info.get("genres", ["Unknown"])
        
        # Ajoute la chanson à tous les genres associés
        for genre in genres:
            genre_dict[genre].append(track["uri"])
        
        if idx % 50 == 0:
            print(f"  -> {idx}/{len(liked_tracks)} pistes analysees...")
    
    print(f"[*] {len(genre_dict)} genres differents trouves dans les chansons likees\n")
    return genre_dict


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
    print("  --confirm           : Confirmer les actions (création/suppression/mise à jour)")
    print("\nExemples :")
    print("  python main.py                    # Dry-run : créer les playlists par classe")
    print("  python main.py --confirm           # Créer réellement les playlists par classe")
    print("  python main.py --analyze           # Analyser les playlists auto")
    print("  python main.py --find              # Trouver les playlists suspectes")
    print("  python main.py --list              # Lister toutes les playlists")
    print("  python main.py --check             # Vérifier les playlists auto")
    print("  python main.py --delete --auto     # Dry-run : supprimer les playlists '(auto)'")
    print("  python main.py --delete --auto --confirm  # Supprimer réellement les playlists '(auto)'")
    print("  python main.py --update            # Dry-run : mettre à jour avec les nouveaux titres")
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
        update_playlists_main()
        return
    
    # Par défaut : créer les playlists par classe
    print("\n[*] Mode : Création de playlists par classe (nomenclature française)\n")
    create_playlists_by_class(confirm=confirm, get_liked_tracks_func=get_liked_tracks, analyze_genres_func=analyze_genres)


if __name__ == "__main__":
    main()
