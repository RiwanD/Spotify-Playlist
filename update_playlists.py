"""
Script de mise à jour des playlists avec les nouveaux titres likés depuis la dernière exécution.
"""
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from credentials import sp
from music_genre import load_class_genres

LAST_UPDATE_FILE = "last_update.json"


def load_last_update_date():
    """Charge la date de la dernière mise à jour depuis le fichier."""
    if Path(LAST_UPDATE_FILE).exists():
        try:
            with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_update_str = data.get("last_update")
                if last_update_str:
                    # Convertir la string ISO en datetime
                    return datetime.fromisoformat(last_update_str.replace("Z", "+00:00"))
        except Exception as e:
            print(f"[!] Erreur lors du chargement de la dernière date de mise à jour : {e}")
    
    return None


def save_last_update_date():
    """Sauvegarde la date actuelle comme dernière date de mise à jour."""
    try:
        current_time = datetime.now(timezone.utc)
        data = {
            "last_update": current_time.isoformat()
        }
        with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[*] Date de dernière mise à jour sauvegardee : {current_time.isoformat()}")
    except Exception as e:
        print(f"[!] Erreur lors de la sauvegarde de la date : {e}")


def get_new_liked_tracks(last_update_date=None):
    """
    Récupère les nouvelles chansons likées depuis la dernière mise à jour.
    
    Args:
        last_update_date: Date de la dernière mise à jour (datetime ou None)
    
    Returns:
        Liste des nouvelles chansons likées avec leur date d'ajout
    """
    print("\n[*] Recuperation des nouvelles chansons likees...")
    new_tracks = []
    results = sp.current_user_saved_tracks(limit=50)
    
    should_stop = False
    while results and not should_stop:
        for item in results["items"]:
            track = item["track"]
            added_at_str = item.get("added_at")
            
            if added_at_str:
                try:
                    added_at = datetime.fromisoformat(added_at_str.replace("Z", "+00:00"))
                    
                    # Si pas de date de dernière mise à jour, prendre toutes les chansons
                    # Sinon, prendre seulement celles ajoutées après la dernière mise à jour
                    if last_update_date is None or added_at > last_update_date:
                        new_tracks.append({
                            "track": track,
                            "added_at": added_at,
                            "uri": track["uri"]
                        })
                    else:
                        # Les chansons sont triées par date décroissante, donc si on trouve
                        # une chanson plus ancienne, on peut s'arrêter
                        if last_update_date and added_at <= last_update_date:
                            should_stop = True
                            break
                except Exception as e:
                    print(f"[!] Erreur lors du parsing de la date : {e}")
                    # En cas d'erreur, inclure la chanson par sécurité
                    new_tracks.append({
                        "track": track,
                        "added_at": None,
                        "uri": track["uri"]
                    })
            else:
                # Si pas de date, inclure par sécurité
                new_tracks.append({
                    "track": track,
                    "added_at": None,
                    "uri": track["uri"]
                })
        
        if not should_stop and results:
            results = sp.next(results) if results.get("next") else None
            time.sleep(0.1)  # Anti rate-limit
    
    print(f"[*] {len(new_tracks)} nouvelle(s) chanson(s) likee(s) trouvee(s)")
    return new_tracks


def analyze_new_tracks_genres(new_tracks):
    """
    Analyse les genres des nouvelles chansons.
    
    Args:
        new_tracks: Liste des nouvelles chansons
    
    Returns:
        Dictionnaire {genre: [track_uris]}
    """
    print("\n[*] Analyse des genres des nouvelles chansons...")
    genre_dict = defaultdict(list)
    artist_cache = {}
    
    for idx, track_info in enumerate(new_tracks, 1):
        track = track_info["track"]
        artist_id = track["artists"][0]["id"]
        
        if artist_id not in artist_cache:
            artist_cache[artist_id] = sp.artist(artist_id)
        
        artist_info = artist_cache[artist_id]
        time.sleep(0.1)  # Pour éviter de trop solliciter l'API
        genres = artist_info.get("genres", ["Unknown"])
        
        # Ajouter la chanson à tous les genres associés
        for genre in genres:
            genre_dict[genre].append(track_info["uri"])
        
        if idx % 20 == 0:
            print(f"  -> {idx}/{len(new_tracks)} nouvelles pistes analysees...")
    
    print(f"[*] {len(genre_dict)} genres differents trouves dans les nouvelles chansons\n")
    return genre_dict


def find_playlists_for_genres(class_genres, genre_dict):
    """
    Trouve les playlists correspondant aux genres trouvés.
    
    Args:
        class_genres: Dictionnaire des classes de genres
        genre_dict: Dictionnaire des genres des nouvelles chansons
    
    Returns:
        Dictionnaire {playlist_name: [track_uris]}
    """
    print("[*] Recherche des playlists correspondantes...")
    
    # Collecter tous les genres connus
    all_known_genres = set()
    for class_info in class_genres.values():
        all_known_genres.update(class_info["genres"])
    
    # Trouver les playlists par classe et par bucket
    playlists_to_update = defaultdict(set)
    
    # Par classe
    for class_label, class_info in class_genres.items():
        class_code = class_info["code"]
        target_genres = class_info["genres"]
        
        # Trouver les genres correspondants
        matching_track_uris = set()
        for genre in target_genres:
            if genre in genre_dict:
                matching_track_uris.update(genre_dict[genre])
        
        if matching_track_uris:
            playlist_name = f"{class_label} (auto)"
            playlists_to_update[playlist_name].update(matching_track_uris)
    
    # Par bucket (sous-genre)
    for class_label, class_info in class_genres.items():
        class_code = class_info["code"]
        buckets = class_info.get("buckets", {})
        genres_by_bucket = class_info.get("genres_by_bucket", {})
        
        for bucket_key, bucket_label in buckets.items():
            bucket_genres = genres_by_bucket.get(bucket_key, [])
            
            # Trouver les genres correspondants
            matching_track_uris = set()
            for genre in bucket_genres:
                if genre in genre_dict:
                    matching_track_uris.update(genre_dict[genre])
            
            if matching_track_uris:
                playlist_name = f"[{class_code}] {bucket_label} (auto)"
                playlists_to_update[playlist_name].update(matching_track_uris)
    
    # Convertir les sets en listes
    playlists_to_update_dict = {
        name: list(track_uris) for name, track_uris in playlists_to_update.items()
    }
    
    print(f"[*] {len(playlists_to_update_dict)} playlist(s) a mettre a jour trouvee(s)")
    return playlists_to_update_dict


def find_playlist_by_name(playlist_name):
    """
    Trouve une playlist par son nom.
    
    Args:
        playlist_name: Nom de la playlist à chercher
    
    Returns:
        ID de la playlist ou None
    """
    playlists = []
    results = sp.current_user_playlists(limit=50)
    
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results.get("next") else None
    
    for playlist in playlists:
        if playlist.get("name") == playlist_name:
            return playlist.get("id")
    
    return None


def update_playlists(playlists_to_update, confirm=False):
    """
    Met à jour les playlists avec les nouvelles chansons.
    
    Args:
        playlists_to_update: Dictionnaire {playlist_name: [track_uris]}
        confirm: Si True, met à jour réellement. Si False, mode dry-run.
    """
    if not playlists_to_update:
        print("[*] Aucune playlist a mettre a jour.")
        return
    
    print("\n" + "=" * 80)
    print("[*] PLAYLISTS A METTRE A JOUR :")
    print("=" * 80)
    
    for playlist_name, track_uris in playlists_to_update.items():
        print(f"\n  -> {playlist_name}")
        print(f"     {len(track_uris)} nouveau(x) titre(s) a ajouter")
    
    if not confirm:
        print("\n[?] Aucune mise a jour effectuee (dry-run).")
        print("   -> Relance avec l'option :  python update_playlists.py --confirm")
        return
    
    print("\n[*] Mise a jour des playlists en cours...\n")
    updated_count = 0
    
    for playlist_name, track_uris in playlists_to_update.items():
        try:
            playlist_id = find_playlist_by_name(playlist_name)
            
            if not playlist_id:
                print(f"  [-] Playlist '{playlist_name}' introuvable, ignoree")
                continue
            
            # Vérifier les titres déjà présents pour éviter les doublons
            existing_tracks = set()
            results = sp.playlist_items(playlist_id, fields="items(track(uri)),next", limit=100)
            while results:
                for item in results.get("items", []):
                    track = item.get("track")
                    if track:
                        existing_tracks.add(track.get("uri"))
                results = sp.next(results) if results.get("next") else None
            
            # Filtrer les titres déjà présents
            new_track_uris = [uri for uri in track_uris if uri not in existing_tracks]
            
            if not new_track_uris:
                print(f"  [i] {playlist_name}: Tous les titres sont deja presents")
                continue
            
            # Ajouter les morceaux par lots de 100 (limite API)
            for i in range(0, len(new_track_uris), 100):
                batch = new_track_uris[i:i+100]
                sp.playlist_add_items(playlist_id, batch)
                time.sleep(0.2)  # Anti rate-limit
            
            updated_count += 1
            print(f"  [+] {playlist_name}: {len(new_track_uris)} titre(s) ajoute(s)")
            time.sleep(0.2)  # Anti rate-limit
            
        except Exception as e:
            print(f"  [-] Erreur lors de la mise a jour de '{playlist_name}': {e}")
    
    print(f"\n[+] Termine. {updated_count}/{len(playlists_to_update)} playlist(s) mise(s) a jour avec succes.")


def main():
    """Fonction principale."""
    confirm = ("--confirm" in sys.argv)
    
    # Récupérer le profil utilisateur
    me = sp.current_user()
    print("[*] Connexion reussie")
    print(f"[*] Utilisateur : {me.get('display_name')} | ID Spotify : {me['id']}")
    
    # Charger la date de dernière mise à jour
    last_update_date = load_last_update_date()
    
    if last_update_date:
        print(f"[*] Derniere mise a jour : {last_update_date.isoformat()}")
        print(f"[*] Recherche des nouvelles chansons likees depuis cette date...")
    else:
        print("[*] Aucune date de derniere mise a jour trouvee.")
        print("[*] Pour initialiser, executez d'abord 'python main.py --confirm'")
        print("[*] Sinon, toutes les chansons likées seront traitées comme nouvelles.")
        response = input("\n[?] Continuer quand meme ? (o/n) : ").strip().lower()
        if response != 'o':
            print("[*] Operation annulee.")
            return
    
    # Récupérer les nouvelles chansons likées
    new_tracks = get_new_liked_tracks(last_update_date)
    
    if not new_tracks:
        print("\n[+] Aucune nouvelle chanson likee depuis la derniere mise a jour.")
        return
    
    # Analyser les genres des nouvelles chansons
    genre_dict = analyze_new_tracks_genres(new_tracks)
    
    # Charger les classes de genres
    class_genres = load_class_genres()
    
    # Trouver les playlists à mettre à jour
    playlists_to_update = find_playlists_for_genres(class_genres, genre_dict)
    
    # Mettre à jour les playlists
    update_playlists(playlists_to_update, confirm=confirm)
    
    # Sauvegarder la date de mise à jour si confirmé
    if confirm:
        save_last_update_date()


if __name__ == "__main__":
    main()

