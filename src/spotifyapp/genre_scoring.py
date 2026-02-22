"""
Module de scoring et d'optimisation des genres musicaux avec descente de gradient.

Ce module implémente :
- Un système de pondération des genres pour chaque playlist
- Un algorithme de descente de gradient pour optimiser les poids
- Des fonctions d'évaluation et de test
"""
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional
import random


class GenreScoringModel:
    """
    Modèle de scoring des genres musicaux avec optimisation par descente de gradient.
    
    Pour chaque bucket/playlist, le modèle maintient des poids pour chaque genre.
    Un titre est scoré en fonction de la somme pondérée de ses genres correspondants.
    """
    
    def __init__(self, class_genres: Dict, initial_weight: float = 1.0):
        """
        Initialise le modèle avec les classes de genres.
        
        Args:
            class_genres: Dictionnaire des classes de genres (depuis load_class_genres)
            initial_weight: Poids initial pour tous les genres (défaut: 1.0)
        """
        self.class_genres = class_genres
        self.initial_weight = initial_weight
        
        # Dictionnaire {bucket_key: {genre: poids}}
        self.genre_weights = {}
        
        # Initialiser les poids pour chaque bucket
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialise les poids pour tous les buckets."""
        for class_label, class_info in self.class_genres.items():
            buckets = class_info.get("buckets", {})
            genres_by_bucket = class_info.get("genres_by_bucket", {})
            
            for bucket_key in buckets.keys():
                bucket_genres = genres_by_bucket.get(bucket_key, [])
                self.genre_weights[bucket_key] = {
                    genre: self.initial_weight for genre in bucket_genres
                }
    
    def score_track(self, track_uri: str, track_genres: List[str], bucket_key: str) -> float:
        """
        Calcule le score d'un titre pour un bucket donné.
        
        Args:
            track_uri: URI du titre
            track_genres: Liste des genres du titre
            bucket_key: Clé du bucket cible
        
        Returns:
            Score du titre (somme pondérée des genres correspondants)
        """
        if bucket_key not in self.genre_weights:
            return 0.0
        
        weights = self.genre_weights[bucket_key]
        track_genres_lower = [g.lower() for g in track_genres]
        
        score = 0.0
        for genre in track_genres_lower:
            # Chercher une correspondance exacte ou partielle
            for bucket_genre, weight in weights.items():
                bucket_genre_lower = bucket_genre.lower()
                if genre == bucket_genre_lower or genre in bucket_genre_lower or bucket_genre_lower in genre:
                    score += weight
                    break  # Ne compter qu'une fois par genre du bucket
        
        return score
    
    def score_tracks_for_bucket(
        self, 
        track_genres_dict: Dict[str, List[str]], 
        bucket_key: str,
        threshold: float = 0.5
    ) -> List[Tuple[str, float]]:
        """
        Score tous les titres pour un bucket et retourne ceux au-dessus du seuil.
        
        Args:
            track_genres_dict: Dictionnaire {track_uri: [genres]}
            bucket_key: Clé du bucket cible
            threshold: Seuil minimum de score (défaut: 0.5)
        
        Returns:
            Liste de tuples (track_uri, score) triés par score décroissant
        """
        scored_tracks = []
        
        for track_uri, track_genres in track_genres_dict.items():
            score = self.score_track(track_uri, track_genres, bucket_key)
            if score >= threshold:
                scored_tracks.append((track_uri, score))
        
        # Trier par score décroissant
        scored_tracks.sort(key=lambda x: x[1], reverse=True)
        return scored_tracks
    
    def compute_loss(
        self,
        track_genres_dict: Dict[str, List[str]],
        bucket_key: str,
        positive_tracks: Set[str],
        negative_tracks: Set[str],
        margin: float = 1.0
    ) -> float:
        """
        Calcule la fonction de perte pour un bucket.
        
        La loss encourage les titres positifs à avoir un score élevé
        et les titres négatifs à avoir un score faible.
        
        Args:
            track_genres_dict: Dictionnaire {track_uri: [genres]}
            bucket_key: Clé du bucket cible
            positive_tracks: Set des URIs de titres qui DEVRAIENT être dans la playlist
            negative_tracks: Set des URIs de titres qui NE DEVRAIENT PAS être dans la playlist
            margin: Marge minimale entre scores positifs et négatifs
        
        Returns:
            Valeur de la loss
        """
        positive_scores = []
        negative_scores = []
        
        # Calculer les scores pour les titres positifs
        for track_uri in positive_tracks:
            if track_uri in track_genres_dict:
                score = self.score_track(track_uri, track_genres_dict[track_uri], bucket_key)
                positive_scores.append(score)
        
        # Calculer les scores pour les titres négatifs
        for track_uri in negative_tracks:
            if track_uri in track_genres_dict:
                score = self.score_track(track_uri, track_genres_dict[track_uri], bucket_key)
                negative_scores.append(score)
        
        if not positive_scores or not negative_scores:
            return 0.0
        
        # Loss = moyenne des max(0, margin - (score_positif - score_négatif))
        # Cela encourage les scores positifs à être supérieurs aux scores négatifs d'au moins 'margin'
        loss = 0.0
        for pos_score in positive_scores:
            for neg_score in negative_scores:
                loss += max(0, margin - (pos_score - neg_score))
        
        return loss / (len(positive_scores) * len(negative_scores))
    
    def compute_gradient(
        self,
        track_genres_dict: Dict[str, List[str]],
        bucket_key: str,
        positive_tracks: Set[str],
        negative_tracks: Set[str],
        margin: float = 1.0
    ) -> Dict[str, float]:
        """
        Calcule le gradient de la loss par rapport aux poids des genres.
        
        Args:
            track_genres_dict: Dictionnaire {track_uri: [genres]}
            bucket_key: Clé du bucket cible
            positive_tracks: Set des URIs de titres positifs
            negative_tracks: Set des URIs de titres négatifs
            margin: Marge minimale
        
        Returns:
            Dictionnaire {genre: gradient} pour ce bucket
        """
        if bucket_key not in self.genre_weights:
            return {}
        
        gradients = defaultdict(float)
        weights = self.genre_weights[bucket_key]
        
        # Pour chaque paire (positif, négatif)
        for pos_uri in positive_tracks:
            if pos_uri not in track_genres_dict:
                continue
            
            pos_genres = [g.lower() for g in track_genres_dict[pos_uri]]
            pos_score = self.score_track(pos_uri, track_genres_dict[pos_uri], bucket_key)
            
            for neg_uri in negative_tracks:
                if neg_uri not in track_genres_dict:
                    continue
                
                neg_genres = [g.lower() for g in track_genres_dict[neg_uri]]
                neg_score = self.score_track(neg_uri, track_genres_dict[neg_uri], bucket_key)
                
                diff = pos_score - neg_score
                
                # Si la marge n'est pas respectée, calculer le gradient
                if diff < margin:
                    # Gradient pour les genres du titre positif
                    for genre in pos_genres:
                        for bucket_genre, weight in weights.items():
                            bucket_genre_lower = bucket_genre.lower()
                            if (genre == bucket_genre_lower or 
                                genre in bucket_genre_lower or 
                                bucket_genre_lower in genre):
                                gradients[bucket_genre] += 1.0
                    
                    # Gradient pour les genres du titre négatif (négatif car on veut les diminuer)
                    for genre in neg_genres:
                        for bucket_genre, weight in weights.items():
                            bucket_genre_lower = bucket_genre.lower()
                            if (genre == bucket_genre_lower or 
                                genre in bucket_genre_lower or 
                                bucket_genre_lower in genre):
                                gradients[bucket_genre] -= 1.0
        
        # Normaliser par le nombre de paires
        num_pairs = len(positive_tracks) * len(negative_tracks)
        if num_pairs > 0:
            for genre in gradients:
                gradients[genre] /= num_pairs
        
        return dict(gradients)
    
    def update_weights(
        self,
        bucket_key: str,
        gradients: Dict[str, float],
        learning_rate: float = 0.01,
        min_weight: float = 0.0,
        max_weight: float = 10.0
    ):
        """
        Met à jour les poids d'un bucket en utilisant le gradient.
        
        Args:
            bucket_key: Clé du bucket
            gradients: Dictionnaire {genre: gradient}
            learning_rate: Taux d'apprentissage
            min_weight: Poids minimum autorisé
            max_weight: Poids maximum autorisé
        """
        if bucket_key not in self.genre_weights:
            return
        
        for genre, gradient in gradients.items():
            if genre in self.genre_weights[bucket_key]:
                new_weight = self.genre_weights[bucket_key][genre] - learning_rate * gradient
                # Clipper les poids entre min et max
                self.genre_weights[bucket_key][genre] = max(min_weight, min(max_weight, new_weight))
    
    def train_bucket(
        self,
        track_genres_dict: Dict[str, List[str]],
        bucket_key: str,
        positive_tracks: Set[str],
        negative_tracks: Set[str],
        learning_rate: float = 0.01,
        num_iterations: int = 100,
        margin: float = 1.0,
        verbose: bool = False
    ) -> List[float]:
        """
        Entraîne le modèle pour un bucket spécifique avec descente de gradient.
        
        Args:
            track_genres_dict: Dictionnaire {track_uri: [genres]}
            bucket_key: Clé du bucket à entraîner
            positive_tracks: Set des URIs de titres positifs
            negative_tracks: Set des URIs de titres négatifs
            learning_rate: Taux d'apprentissage
            num_iterations: Nombre d'itérations
            margin: Marge minimale
            verbose: Afficher la progression
        
        Returns:
            Liste des valeurs de loss à chaque itération
        """
        loss_history = []
        
        for iteration in range(num_iterations):
            # Calculer la loss
            loss = self.compute_loss(
                track_genres_dict, bucket_key, positive_tracks, negative_tracks, margin
            )
            loss_history.append(loss)
            
            # Calculer le gradient
            gradients = self.compute_gradient(
                track_genres_dict, bucket_key, positive_tracks, negative_tracks, margin
            )
            
            # Mettre à jour les poids
            self.update_weights(bucket_key, gradients, learning_rate)
            
            if verbose and (iteration % 10 == 0 or iteration == num_iterations - 1):
                print(f"  Iteration {iteration}: Loss = {loss:.4f}")
        
        return loss_history
    
    def save_weights(self, filepath: str):
        """Sauvegarde les poids dans un fichier JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.genre_weights, f, ensure_ascii=False, indent=2)
    
    def load_weights(self, filepath: str):
        """Charge les poids depuis un fichier JSON."""
        if Path(filepath).exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                self.genre_weights = json.load(f)
        else:
            print(f"[!] Fichier de poids introuvable : {filepath}")
    
    def get_top_genres(self, bucket_key: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Retourne les genres avec les poids les plus élevés pour un bucket.
        
        Args:
            bucket_key: Clé du bucket
            top_k: Nombre de genres à retourner
        
        Returns:
            Liste de tuples (genre, poids) triés par poids décroissant
        """
        if bucket_key not in self.genre_weights:
            return []
        
        genres_with_weights = list(self.genre_weights[bucket_key].items())
        genres_with_weights.sort(key=lambda x: x[1], reverse=True)
        
        return genres_with_weights[:top_k]


def create_training_data_from_playlists(
    track_genres_dict: Dict[str, List[str]],
    bucket_key: str,
    current_playlist_tracks: Set[str],
    all_tracks: Set[str],
    negative_ratio: float = 0.5
) -> Tuple[Set[str], Set[str]]:
    """
    Crée des données d'entraînement à partir d'une playlist existante.
    
    Les titres dans la playlist sont considérés comme positifs.
    Les titres négatifs sont sélectionnés aléatoirement parmi les autres titres.
    
    Args:
        track_genres_dict: Dictionnaire {track_uri: [genres]}
        bucket_key: Clé du bucket
        current_playlist_tracks: Set des URIs des titres actuellement dans la playlist
        all_tracks: Set de tous les URIs disponibles
        negative_ratio: Ratio de titres négatifs par rapport aux positifs
    
    Returns:
        Tuple (positive_tracks, negative_tracks)
    """
    positive_tracks = current_playlist_tracks.copy()
    
    # Sélectionner des titres négatifs (pas dans la playlist)
    negative_candidates = all_tracks - current_playlist_tracks
    num_negative = int(len(positive_tracks) * negative_ratio)
    negative_tracks = set(random.sample(list(negative_candidates), min(num_negative, len(negative_candidates))))
    
    return positive_tracks, negative_tracks


def evaluate_model(
    model: GenreScoringModel,
    track_genres_dict: Dict[str, List[str]],
    bucket_key: str,
    positive_tracks: Set[str],
    negative_tracks: Set[str],
    threshold: float = 0.5
) -> Dict[str, float]:
    """
    Évalue les performances du modèle.
    
    Args:
        model: Modèle à évaluer
        track_genres_dict: Dictionnaire {track_uri: [genres]}
        bucket_key: Clé du bucket
        positive_tracks: Set des URIs de titres positifs
        negative_tracks: Set des URIs de titres négatifs
        threshold: Seuil de score pour la classification
    
    Returns:
        Dictionnaire avec les métriques (precision, recall, f1, accuracy)
    """
    # Prédire les scores
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    
    for track_uri in positive_tracks:
        if track_uri in track_genres_dict:
            score = model.score_track(track_uri, track_genres_dict[track_uri], bucket_key)
            if score >= threshold:
                true_positives += 1
            else:
                false_negatives += 1
    
    for track_uri in negative_tracks:
        if track_uri in track_genres_dict:
            score = model.score_track(track_uri, track_genres_dict[track_uri], bucket_key)
            if score >= threshold:
                false_positives += 1
            else:
                true_negatives += 1
    
    # Calculer les métriques
    total = true_positives + false_positives + true_negatives + false_negatives
    if total == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
    
    accuracy = (true_positives + true_negatives) / total
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives
    }
