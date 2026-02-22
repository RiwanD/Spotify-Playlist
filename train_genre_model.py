"""
Script d'entraînement du modèle de scoring des genres avec descente de gradient.

Usage:
    python train_genre_model.py --bucket 4.3 --iterations 100 --learning-rate 0.01
    python train_genre_model.py --all-buckets --iterations 50
    python train_genre_model.py --bucket 4.3 --save-tracks  # Sauvegarder les listes dans un fichier
"""
import sys
import argparse
import json
from collections import defaultdict
from pathlib import Path
from credentials import sp
from music_genre import load_class_genres
from genre_scoring import (
    GenreScoringModel, 
    create_training_data_from_playlists,
    evaluate_model
)


def get_playlist_tracks(playlist_name: str) -> set:
    """Récupère les URIs des titres d'une playlist."""
    playlists = sp.current_user_playlists(limit=50)
    playlist_id = None
    
    while playlists:
        for playlist in playlists["items"]:
            if playlist["name"] == playlist_name:
                playlist_id = playlist["id"]
                break
        if playlist_id:
            break
        playlists = sp.next(playlists) if playlists.get("next") else None
    
    if not playlist_id:
        return set()
    
    tracks = set()
    results = sp.playlist_items(playlist_id, fields="items(track(uri)),next", limit=100)
    while results:
        for item in results.get("items", []):
            track = item.get("track")
            if track:
                tracks.add(track.get("uri"))
        results = sp.next(results) if results.get("next") else None
    
    return tracks


def get_all_liked_tracks() -> set:
    """Récupère tous les URIs des titres likés."""
    tracks = set()
    results = sp.current_user_saved_tracks(limit=50)
    while results:
        for item in results["items"]:
            track = item["track"]
            tracks.add(track["uri"])
        results = sp.next(results) if results["next"] else None
    return tracks


def get_track_info(track_uri: str) -> dict:
    """Récupère les informations d'un titre (nom, artiste)."""
    try:
        track_id = track_uri.split(":")[-1]
        track = sp.track(track_id)
        return {
            "name": track["name"],
            "artists": ", ".join([artist["name"] for artist in track["artists"]]),
            "uri": track_uri
        }
    except Exception as e:
        return {
            "name": "Unknown",
            "artists": "Unknown",
            "uri": track_uri
        }


def analyze_tracks_genres(track_uris: set, use_cache=True, force_refresh=False) -> dict:
    """
    Analyse les genres de tous les titres en utilisant le cache.
    
    Args:
        track_uris: Set des URIs des titres
        use_cache: Si True, utilise le cache
        force_refresh: Si True, force la mise à jour depuis l'API
    """
    print("\n[*] Analyse des genres des titres...")
    
    if use_cache:
        from genre_cache import get_cache
        cache = get_cache()
        
        # Afficher les stats du cache
        stats = cache.get_cache_stats()
        print(f"[*] Cache: {stats['tracks_cached']} titres, {stats['artists_cached']} artistes en cache")
        
        # Analyser avec le cache
        def progress_callback(idx, total):
            print(f"  -> {idx}/{total} titres analyses...")
        
        track_genres_dict = cache.analyze_tracks_genres(
            list(track_uris),
            force_refresh=force_refresh,
            progress_callback=progress_callback
        )
    else:
        # Méthode originale sans cache
        track_genres_dict = {}
        artist_cache = {}
        
        for idx, track_uri in enumerate(track_uris, 1):
            # Récupérer les infos du titre
            track = sp.track(track_uri.split(":")[-1])
            artist_id = track["artists"][0]["id"]
            
            if artist_id not in artist_cache:
                artist_cache[artist_id] = sp.artist(artist_id)
            
            artist_info = artist_cache[artist_id]
            genres = artist_info.get("genres", ["Unknown"])
            track_genres_dict[track_uri] = genres
            
            if idx % 50 == 0:
                print(f"  -> {idx}/{len(track_uris)} titres analyses...")
    
    print(f"[*] {len(track_genres_dict)} titres analyses\n")
    return track_genres_dict


def train_bucket_model(
    bucket_key: str,
    bucket_label: str,
    class_code: str,
    track_genres_dict: dict,
    all_tracks: set,
    iterations: int = 100,
    learning_rate: float = 0.01,
    margin: float = 1.0,
    save_tracks: bool = False
):
    """Entraîne le modèle pour un bucket spécifique."""
    print(f"\n{'='*80}")
    print(f"[*] Entrainement pour le bucket {bucket_key}: {bucket_label}")
    print(f"{'='*80}")
    
    # Créer le modèle
    class_genres = load_class_genres()
    model = GenreScoringModel(class_genres)
    
    # Charger les poids existants si disponibles
    weights_file = f"weights_{class_code}_{bucket_key.replace('.', '_')}.json"
    try:
        model.load_weights(weights_file)
        print(f"[*] Poids existants charges depuis {weights_file}")
    except:
        print(f"[*] Initialisation avec poids par defaut")
    
    # Récupérer les titres de la playlist actuelle
    playlist_name = f"[{class_code}] {bucket_label} (auto)"
    current_playlist_tracks = get_playlist_tracks(playlist_name)
    
    if not current_playlist_tracks:
        print(f"[!] Playlist '{playlist_name}' introuvable ou vide")
        print("[!] Impossible d'entrainer sans donnees d'entrainement")
        return None
    
    print(f"[*] {len(current_playlist_tracks)} titres trouves dans la playlist")
    
    # Créer les données d'entraînement
    positive_tracks, negative_tracks = create_training_data_from_playlists(
        track_genres_dict, bucket_key, current_playlist_tracks, all_tracks
    )
    
    print(f"[*] Donnees d'entrainement:")
    print(f"    - Titres positifs: {len(positive_tracks)}")
    print(f"    - Titres negatifs: {len(negative_tracks)}")
    
    # Afficher les listes de titres
    print("\n[*] Liste des titres positifs (dans la playlist):")
    positive_tracks_list = []
    for idx, track_uri in enumerate(sorted(positive_tracks), 1):
        track_info = get_track_info(track_uri)
        genres = track_genres_dict.get(track_uri, [])
        genres_str = ", ".join(genres[:3]) + ("..." if len(genres) > 3 else "")
        print(f"    {idx:3d}. {track_info['name']} - {track_info['artists']}")
        print(f"        Genres: {genres_str}")
        positive_tracks_list.append({
            "name": track_info['name'],
            "artists": track_info['artists'],
            "uri": track_uri,
            "genres": genres
        })
    
    print("\n[*] Liste des titres negatifs (hors playlist):")
    negative_tracks_list = []
    for idx, track_uri in enumerate(sorted(negative_tracks), 1):
        track_info = get_track_info(track_uri)
        genres = track_genres_dict.get(track_uri, [])
        genres_str = ", ".join(genres[:3]) + ("..." if len(genres) > 3 else "")
        print(f"    {idx:3d}. {track_info['name']} - {track_info['artists']}")
        print(f"        Genres: {genres_str}")
        negative_tracks_list.append({
            "name": track_info['name'],
            "artists": track_info['artists'],
            "uri": track_uri,
            "genres": genres
        })
    
    # Sauvegarder dans un fichier si demandé
    if save_tracks:
        tracks_file = f"training_tracks_{class_code}_{bucket_key.replace('.', '_')}.json"
        tracks_data = {
            "bucket_key": bucket_key,
            "bucket_label": bucket_label,
            "class_code": class_code,
            "positive_tracks": positive_tracks_list,
            "negative_tracks": negative_tracks_list,
            "positive_count": len(positive_tracks_list),
            "negative_count": len(negative_tracks_list)
        }
        with open(tracks_file, 'w', encoding='utf-8') as f:
            json.dump(tracks_data, f, ensure_ascii=False, indent=2)
        print(f"\n[+] Listes sauvegardees dans {tracks_file}")
    
    # Évaluer avant entraînement
    print("\n[*] Evaluation avant entrainement:")
    metrics_before = evaluate_model(model, track_genres_dict, bucket_key, positive_tracks, negative_tracks)
    print(f"    Accuracy: {metrics_before['accuracy']:.3f}")
    print(f"    Precision: {metrics_before['precision']:.3f}")
    print(f"    Recall: {metrics_before['recall']:.3f}")
    print(f"    F1: {metrics_before['f1']:.3f}")
    
    # Entraîner le modèle
    print(f"\n[*] Entrainement en cours ({iterations} iterations)...")
    loss_history = model.train_bucket(
        track_genres_dict,
        bucket_key,
        positive_tracks,
        negative_tracks,
        learning_rate=learning_rate,
        num_iterations=iterations,
        margin=margin,
        verbose=True
    )
    
    # Évaluer après entraînement
    print("\n[*] Evaluation apres entrainement:")
    metrics_after = evaluate_model(model, track_genres_dict, bucket_key, positive_tracks, negative_tracks)
    print(f"    Accuracy: {metrics_after['accuracy']:.3f}")
    print(f"    Precision: {metrics_after['precision']:.3f}")
    print(f"    Recall: {metrics_after['recall']:.3f}")
    print(f"    F1: {metrics_after['f1']:.3f}")
    
    # Afficher les genres les plus importants
    print("\n[*] Top 10 genres les plus importants:")
    top_genres = model.get_top_genres(bucket_key, top_k=10)
    for idx, (genre, weight) in enumerate(top_genres, 1):
        print(f"    {idx:2d}. {genre}: {weight:.3f}")
    
    # Sauvegarder les poids
    model.save_weights(weights_file)
    print(f"\n[+] Poids sauvegardes dans {weights_file}")
    
    return model


def main():
    parser = argparse.ArgumentParser(description="Entraîner le modèle de scoring des genres")
    parser.add_argument("--bucket", type=str, help="Clé du bucket à entraîner (ex: 4.3)")
    parser.add_argument("--all-buckets", action="store_true", help="Entraîner tous les buckets")
    parser.add_argument("--iterations", type=int, default=100, help="Nombre d'itérations")
    parser.add_argument("--learning-rate", type=float, default=0.01, help="Taux d'apprentissage")
    parser.add_argument("--margin", type=float, default=1.0, help="Marge minimale")
    parser.add_argument("--save-tracks", action="store_true", help="Sauvegarder les listes de titres dans un fichier JSON")
    parser.add_argument("--no-cache", action="store_true", help="Desactiver l'utilisation du cache")
    parser.add_argument("--refresh-cache", action="store_true", help="Forcer la mise a jour du cache depuis l'API")
    
    args = parser.parse_args()
    
    if not args.bucket and not args.all_buckets:
        print("[!] Veuillez specifier --bucket ou --all-buckets")
        return
    
    # Récupérer tous les titres likés
    print("[*] Recuperation des titres likes...")
    all_tracks = get_all_liked_tracks()
    print(f"[*] {len(all_tracks)} titres likes trouves")
    
    # Analyser les genres
    use_cache = not args.no_cache
    force_refresh = args.refresh_cache
    track_genres_dict = analyze_tracks_genres(all_tracks, use_cache=use_cache, force_refresh=force_refresh)
    
    # Charger les classes de genres
    class_genres = load_class_genres()
    
    if args.all_buckets:
        # Entraîner tous les buckets
        for class_label, class_info in class_genres.items():
            class_code = class_info["code"]
            buckets = class_info.get("buckets", {})
            
            for bucket_key, bucket_label in buckets.items():
                train_bucket_model(
                    bucket_key,
                    bucket_label,
                    class_code,
                    track_genres_dict,
                    all_tracks,
                    iterations=args.iterations,
                    learning_rate=args.learning_rate,
                    margin=args.margin,
                    save_tracks=args.save_tracks
                )
    else:
        # Entraîner un bucket spécifique
        bucket_key = args.bucket
        
        # Trouver le bucket dans les classes
        bucket_found = False
        for class_label, class_info in class_genres.items():
            class_code = class_info["code"]
            buckets = class_info.get("buckets", {})
            
            if bucket_key in buckets:
                bucket_label = buckets[bucket_key]
                train_bucket_model(
                    bucket_key,
                    bucket_label,
                    class_code,
                    track_genres_dict,
                    all_tracks,
                    iterations=args.iterations,
                    learning_rate=args.learning_rate,
                    margin=args.margin
                )
                bucket_found = True
                break
        
        if not bucket_found:
            print(f"[!] Bucket '{bucket_key}' introuvable")


if __name__ == "__main__":
    main()
