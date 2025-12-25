import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import defaultdict
from credentials import sp
import json
import os
import time
import sys
from pathlib import Path

# Les fonctions get_liked_tracks() et analyze_genres() sont définies dans main.py
# Elles peuvent être passées en paramètres pour éviter les imports circulaires

def load_class_genres():
    """Charge les fichiers de genres et collecte tous les genres par classe."""
    genres_dir = Path("genres")
    class_data = []
    
    print("\n[*] Chargement des fichiers de genres...")
    for json_file in sorted(genres_dir.glob("classe_*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file_path"] = json_file  # Garder le chemin du fichier
                class_data.append(data)
                print(f"  -> {json_file.name}: {data.get('class_label', 'N/A')}")
        except Exception as e:
            print(f"  [-] Erreur lors du chargement de {json_file.name}: {e}")
    
    print(f"[*] {len(class_data)} classe(s) chargee(s)\n")
    
    # Collecter tous les genres par classe et par bucket
    class_genres = {}
    for data in class_data:
        class_label = data.get("class_label", "Unknown")
        class_code = data.get("class_code", "?")
        
        # Collecter tous les genres de tous les buckets
        all_genres = set()
        genres_by_bucket = data.get("genres_by_bucket", {})
        buckets = data.get("buckets", {})
        
        for bucket_genres in genres_by_bucket.values():
            all_genres.update(bucket_genres)
        
        class_genres[class_label] = {
            "code": class_code,
            "genres": list(all_genres),
            "genre_count": len(all_genres),
            "data": data,  # Garder les données complètes pour pouvoir les modifier
            "buckets": buckets,  # Garder les buckets avec leurs labels
            "genres_by_bucket": genres_by_bucket  # Garder les genres par bucket
        }
        print(f"[*] Classe {class_code}: {class_label}")
        print(f"    -> {len(all_genres)} genres differents")
        print(f"    -> {len(buckets)} bucket(s) (sous-genres)")
    
    return class_genres


def add_genre_to_class(class_genres, genre, class_label, bucket_key=None):
    """
    Ajoute un genre à une classe et sauvegarde dans le fichier JSON.
    
    Args:
        class_genres: Dictionnaire des classes de genres
        genre: Le genre à ajouter
        class_label: Le label de la classe cible
        bucket_key: La clé du bucket (optionnel, si None, ajoute au premier bucket)
    """
    if class_label not in class_genres:
        print(f"  [-] Erreur : Classe '{class_label}' introuvable")
        return False
    
    class_info = class_genres[class_label]
    class_data = class_info["data"]
    file_path = class_data.get("_file_path")
    
    if file_path is None:
        print(f"  [-] Erreur : Chemin du fichier introuvable pour la classe '{class_label}'")
        return False
    
    genres_by_bucket = class_data.get("genres_by_bucket", {})
    
    # Si bucket_key n'est pas spécifié, utiliser le premier bucket disponible
    if bucket_key is None:
        if genres_by_bucket:
            bucket_key = list(genres_by_bucket.keys())[0]
        else:
            # Créer un nouveau bucket par défaut
            bucket_key = "1.0"
            if "buckets" not in class_data:
                class_data["buckets"] = {}
            class_data["buckets"][bucket_key] = "Autres"
    
    # Ajouter le genre au bucket
    if bucket_key not in genres_by_bucket:
        genres_by_bucket[bucket_key] = []
    
    if genre not in genres_by_bucket[bucket_key]:
        genres_by_bucket[bucket_key].append(genre)
        class_data["genres_by_bucket"] = genres_by_bucket
        
        # Mettre à jour le dictionnaire class_genres
        all_genres = set()
        for bucket_genres in genres_by_bucket.values():
            all_genres.update(bucket_genres)
        class_info["genres"] = list(all_genres)
        class_info["genre_count"] = len(all_genres)
        
        # Sauvegarder dans le fichier JSON
        try:
            # Retirer le champ temporaire avant de sauvegarder
            save_data = {k: v for k, v in class_data.items() if k != "_file_path"}
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"  [+] Genre '{genre}' ajoute a la classe '{class_label}' (bucket {bucket_key})")
            print(f"     Fichier sauvegarde : {file_path.name}")
            return True
        except Exception as e:
            print(f"  [-] Erreur lors de la sauvegarde : {e}")
            return False
    
    print(f"  [i] Le genre '{genre}' existe deja dans la classe '{class_label}'")
    return True


def handle_unknown_genres(genre_dict, class_genres):
    """
    Détecte les genres inconnus et permet à l'utilisateur de les classer.
    
    Args:
        genre_dict: Dictionnaire des genres trouvés dans les chansons likées
        class_genres: Dictionnaire des classes de genres connus
    """
    # Collecter tous les genres connus
    all_known_genres = set()
    for class_info in class_genres.values():
        all_known_genres.update(class_info["genres"])
    
    # Trouver les genres inconnus
    unknown_genres = set(genre_dict.keys()) - all_known_genres
    
    if not unknown_genres:
        return
    
    print("\n" + "=" * 80)
    print("[!] ATTENTION : Genres inconnus detectes")
    print("=" * 80)
    print(f"[*] {len(unknown_genres)} genre(s) trouve(s) dans vos chansons likées ne correspondent a aucune classe connue :\n")
    
    for idx, genre in enumerate(sorted(unknown_genres), 1):
        track_count = len(genre_dict[genre])
        print(f"  {idx}. {genre} ({track_count} titre(s))")
    
    print("\n[*] Classes disponibles :")
    for idx, (class_label, class_info) in enumerate(class_genres.items(), 1):
        print(f"  {idx}. [{class_info['code']}] {class_label}")
    
    print("\n[?] Voulez-vous classer ces genres dans une classe existante ?")
    print("    (Entrez 'o' pour oui, 'n' pour non, ou 'q' pour quitter)")
    
    response = input("    Votre choix : ").strip().lower()
    
    if response == 'q':
        print("[*] Operation annulee.")
        return
    
    if response != 'o':
        print("[*] Genres inconnus ignores. Les chansons correspondantes ne seront pas classees.")
        return
    
    # Traiter chaque genre inconnu
    for genre in sorted(unknown_genres):
        print(f"\n[*] Genre : {genre} ({len(genre_dict[genre])} titre(s))")
        print("[?] Dans quelle classe voulez-vous le classer ?")
        print("    (Entrez le numero de la classe, ou 's' pour sauter ce genre)")
        
        choice = input("    Votre choix : ").strip()
        
        if choice.lower() == 's':
            print(f"  [i] Genre '{genre}' ignore.")
            continue
        
        try:
            class_idx = int(choice) - 1
            class_labels = list(class_genres.keys())
            
            if 0 <= class_idx < len(class_labels):
                selected_class = class_labels[class_idx]
                class_info = class_genres[selected_class]
                
                print(f"  [*] Ajout du genre '{genre}' a la classe '{selected_class}'")
                
                # Afficher les buckets disponibles
                buckets = class_info["data"].get("buckets", {})
                if buckets:
                    print("  [*] Buckets disponibles :")
                    for idx, (bucket_key, bucket_label) in enumerate(buckets.items(), 1):
                        print(f"      {idx}. [{bucket_key}] {bucket_label}")
                    print("      (Entrez le numero du bucket, ou 'a' pour auto-selection)")
                    
                    bucket_choice = input("      Votre choix : ").strip().lower()
                    
                    if bucket_choice == 'a':
                        bucket_key = None
                    else:
                        try:
                            bucket_idx = int(bucket_choice) - 1
                            bucket_keys = list(buckets.keys())
                            if 0 <= bucket_idx < len(bucket_keys):
                                bucket_key = bucket_keys[bucket_idx]
                            else:
                                bucket_key = None
                        except ValueError:
                            bucket_key = None
                else:
                    bucket_key = None
                
                add_genre_to_class(class_genres, genre, selected_class, bucket_key)
            else:
                print(f"  [-] Numero invalide. Genre '{genre}' ignore.")
        except ValueError:
            print(f"  [-] Entree invalide. Genre '{genre}' ignore.")
    
    print("\n[*] Traitement des genres inconnus termine.")


def create_playlists_by_class(confirm=False, get_liked_tracks_func=None, analyze_genres_func=None):
    """Crée des playlists par classe selon la nomenclature française."""
    # Récupère ton user_id
    user_id = sp.current_user()["id"]
    
    # Charger les genres par classe
    class_genres = load_class_genres()
    
    # Utiliser les fonctions passées en paramètres ou les importer depuis main
    if get_liked_tracks_func is None or analyze_genres_func is None:
        # Import local pour éviter les imports circulaires
        import main as main_module
        get_liked_tracks_func = main_module.get_liked_tracks
        analyze_genres_func = main_module.analyze_genres
    
    # Récupère toutes tes chansons likées
    liked_tracks = get_liked_tracks_func()
    
    # Analyse des genres
    genre_dict = analyze_genres_func(liked_tracks)
    
    # Détecter et gérer les genres inconnus (peut modifier class_genres)
    handle_unknown_genres(genre_dict, class_genres)
    
    # Associer les chansons aux classes et aux buckets (sous-genres)
    # Note : Un titre peut apparaître dans plusieurs playlists si ses genres correspondent à plusieurs classes/buckets
    print("[*] Association des chansons aux classes et sous-genres...")
    class_playlists = []
    bucket_playlists = []
    
    # Playlists par classe (comme avant)
    for class_label, class_info in class_genres.items():
        class_code = class_info["code"]
        target_genres = class_info["genres"]
        
        # Trouver toutes les chansons correspondant aux genres de cette classe
        # Utilisation d'un set() pour éviter les doublons dans la même playlist
        track_uris = set()
        for genre in target_genres:
            if genre in genre_dict:
                track_uris.update(genre_dict[genre])
        
        track_uris_list = list(track_uris)
        
        # Ne créer que les playlists avec au moins 3 titres
        if len(track_uris_list) < 3:
            print(f"  -> {class_code}: {class_label}")
            print(f"     {len(track_uris_list)} titres trouves (IGNORE - moins de 3 titres)")
            continue
        
        # Limiter à 1000 morceaux par playlist (API restriction)
        track_uris_limited = track_uris_list[:1000]
        
        playlist_name = f"{class_label} (auto)"
        class_playlists.append({
            "class_code": class_code,
            "class_label": class_label,
            "playlist_name": playlist_name,
            "track_uris": track_uris_limited,
            "total_tracks": len(track_uris_list),
            "genres_count": len(target_genres),
            "type": "class"
        })
        
        print(f"  -> {class_code}: {class_label}")
        print(f"     {len(track_uris_list)} titres trouves ({len(track_uris_limited)} seront ajoutes)")
    
    # Playlists par bucket (sous-genre)
    print("\n[*] Association des chansons aux sous-genres (buckets)...")
    for class_label, class_info in class_genres.items():
        class_code = class_info["code"]
        buckets = class_info.get("buckets", {})
        genres_by_bucket = class_info.get("genres_by_bucket", {})
        
        for bucket_key, bucket_label in buckets.items():
            # Pour les buckets 1.4, 1.5, 1.6, créer des playlists spécifiques
            # Pour les autres, créer des playlists par bucket
            bucket_genres = genres_by_bucket.get(bucket_key, [])
            
            if not bucket_genres:
                continue
            
            # Trouver toutes les chansons correspondant aux genres de ce bucket
            track_uris = set()
            for genre in bucket_genres:
                if genre in genre_dict:
                    track_uris.update(genre_dict[genre])
            
            track_uris_list = list(track_uris)
            
            # Ne créer que les playlists avec au moins 3 titres
            if len(track_uris_list) < 3:
                print(f"  -> {bucket_key}: {bucket_label}")
                print(f"     {len(track_uris_list)} titres trouves (IGNORE - moins de 3 titres)")
                continue
            
            track_uris_limited = track_uris_list[:1000]
            
            # Nom de la playlist : préfixer avec le code de classe pour regroupement visuel et organisation en dossiers
            playlist_name = f"[{class_code}] {bucket_label} (auto)"
            
            bucket_playlists.append({
                "class_code": class_code,
                "bucket_key": bucket_key,
                "bucket_label": bucket_label,
                "playlist_name": playlist_name,
                "track_uris": track_uris_limited,
                "total_tracks": len(track_uris_list),
                "genres_count": len(bucket_genres),
                "type": "bucket"
            })
            
            print(f"  -> {bucket_key}: {bucket_label}")
            print(f"     {len(track_uris_list)} titres trouves ({len(track_uris_limited)} seront ajoutes)")
    
    # Combiner toutes les playlists
    all_playlists = class_playlists + bucket_playlists
    
    # Affichage des playlists qui seraient créées
    print("\n" + "=" * 80)
    print("[*] PLAYLISTS QUI SERAIENT CREEES :")
    print("=" * 80)
    print("\n[*] Par classe :")
    for idx, playlist_info in enumerate(class_playlists, 1):
        print(f"{idx:3d}. {playlist_info['playlist_name']}")
        print(f"     Classe: {playlist_info['class_code']} | {playlist_info['total_tracks']} titres")
        print(f"     Genres: {playlist_info['genres_count']} genres differents")
    
    print("\n[*] Par sous-genre (bucket) :")
    for idx, playlist_info in enumerate(bucket_playlists, 1):
        print(f"{idx:3d}. {playlist_info['playlist_name']}")
        print(f"     Bucket: {playlist_info['bucket_key']} | {playlist_info['total_tracks']} titres")
        print(f"     Genres: {playlist_info['genres_count']} genres differents")
    print()
    
    # Validation et création
    if not confirm:
        print("[?] Aucune playlist creee (dry-run).")
        print("   -> Relance avec l'option :  python main.py --confirm")
        print(f"\n[*] {len(all_playlists)} playlist(s) seraient creees ({len(class_playlists)} par classe, {len(bucket_playlists)} par sous-genre).")
    else:
        print(f"[*] Creation de {len(all_playlists)} playlist(s) en cours...\n")
        created_count = 0
        for idx, playlist_info in enumerate(all_playlists, 1):
            try:
                # Crée la playlist
                if playlist_info["type"] == "class":
                    description = f"Playlist auto-generee pour la classe {playlist_info['class_code']}: {playlist_info['class_label']}"
                else:  # bucket
                    description = f"Playlist auto-generee pour le sous-genre {playlist_info['bucket_key']} ({playlist_info['bucket_label']}) de la classe {playlist_info['class_code']}"
                
                playlist = sp.user_playlist_create(
                    user=user_id,
                    name=playlist_info["playlist_name"],
                    public=False,
                    description=description
                )
                
                # Ajoute les morceaux par lots de 100 (limite API)
                track_uris = playlist_info["track_uris"]
                for i in range(0, len(track_uris), 100):
                    batch = track_uris[i:i+100]
                    sp.playlist_add_items(playlist["id"], batch)
                    time.sleep(0.2)  # Anti rate-limit
                
                created_count += 1
                print(f"  [{idx}/{len(all_playlists)}] [+] Playlist creee : {playlist_info['playlist_name']} ({len(track_uris)} titres)")
                time.sleep(0.2)  # Anti rate-limit
            except Exception as e:
                print(f"  [{idx}/{len(all_playlists)}] [-] Erreur lors de la creation de {playlist_info['playlist_name']}: {e}")
        
        print(f"\n[+] Termine. {created_count}/{len(all_playlists)} playlist(s) creee(s) avec succes.")
        
        # Sauvegarder la date de dernière mise à jour
        from datetime import datetime, timezone
        import json
        from pathlib import Path
        try:
            last_update_file = Path("last_update.json")
            current_time = datetime.now(timezone.utc)
            data = {
                "last_update": current_time.isoformat()
            }
            with open(last_update_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[*] Date de derniere mise a jour sauvegardee : {current_time.isoformat()}")
        except Exception as e:
            print(f"[!] Erreur lors de la sauvegarde de la date : {e}")


if __name__ == "__main__":
    # --- Test : récupérer ton profil ---
    me = sp.current_user()
    confirm = ("--confirm" in sys.argv)
    
    print("[*] Connexion reussie")
    print(f"[*] Utilisateur : {me.get('display_name')} | ID Spotify : {me['id']}")
    
    create_playlists_by_class(confirm=confirm)

