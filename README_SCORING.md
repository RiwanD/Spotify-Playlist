# Système de Scoring Pondéré des Genres Musicaux

Ce système utilise des algorithmes de descente de gradient pour optimiser les poids des genres musicaux dans chaque playlist.

## Architecture

### 1. Module `genre_scoring.py`

Contient la classe `GenreScoringModel` qui implémente :
- **Scoring des titres** : Chaque titre reçoit un score basé sur la somme pondérée de ses genres correspondants
- **Fonction de perte (Loss)** : Mesure la différence entre les scores des titres positifs et négatifs
- **Descente de gradient** : Optimise les poids des genres pour minimiser la loss
- **Évaluation** : Calcule les métriques (precision, recall, F1, accuracy)

### 2. Script d'entraînement `train_genre_model.py`

Permet d'entraîner le modèle pour un ou plusieurs buckets :
- Utilise les playlists existantes comme données d'entraînement
- Les titres dans la playlist = exemples positifs
- Les titres hors playlist = exemples négatifs
- Optimise les poids via descente de gradient

### 3. Intégration dans `music_genre.py`

Le système de scoring peut être activé avec l'option `--scoring` lors de la création des playlists.

## Utilisation

### Étape 1 : Entraîner le modèle

Pour entraîner le modèle sur un bucket spécifique (ex: House - 4.3) :

```bash
python train_genre_model.py --bucket 4.3 --iterations 100 --learning-rate 0.01
```

Pour entraîner tous les buckets :

```bash
python train_genre_model.py --all-buckets --iterations 50
```

**Paramètres :**
- `--bucket` : Clé du bucket à entraîner (ex: "4.3")
- `--all-buckets` : Entraîner tous les buckets
- `--iterations` : Nombre d'itérations de descente de gradient (défaut: 100)
- `--learning-rate` : Taux d'apprentissage (défaut: 0.01)
- `--margin` : Marge minimale entre scores positifs et négatifs (défaut: 1.0)

### Étape 2 : Créer les playlists avec scoring

Une fois le modèle entraîné, utilisez l'option `--scoring` :

```bash
python main.py --scoring --confirm
```

Le système chargera automatiquement les poids entraînés depuis les fichiers `weights_*.json`.

### Étape 3 : Évaluer les résultats

Le script d'entraînement affiche automatiquement :
- Les métriques avant et après entraînement
- Les top 10 genres les plus importants pour chaque bucket
- L'historique de la loss

## Fonctionnement du Scoring

### Calcul du score

Pour un titre avec genres `[genre1, genre2, ...]` et un bucket avec poids `{genre: poids}` :

```
score = Σ poids[genre] pour chaque genre du titre qui correspond au bucket
```

### Fonction de perte

La loss encourage les titres positifs à avoir un score supérieur aux titres négatifs :

```
loss = moyenne(max(0, margin - (score_positif - score_négatif)))
```

### Descente de gradient

À chaque itération :
1. Calculer la loss actuelle
2. Calculer le gradient de la loss par rapport aux poids
3. Mettre à jour les poids : `poids = poids - learning_rate * gradient`

## Fichiers générés

- `weights_{class_code}_{bucket_key}.json` : Poids optimisés pour chaque bucket
  - Exemple : `weights_4_4_3.json` pour le bucket 4.3 de la classe 4

## Avantages du système de scoring

1. **Adaptatif** : Les poids s'adaptent automatiquement à votre bibliothèque musicale
2. **Précis** : Meilleure sélection des titres pertinents pour chaque playlist
3. **Optimisé** : Utilise des algorithmes d'optimisation mathématique
4. **Évaluable** : Métriques claires pour mesurer les performances

## Comparaison avec le filtrage simple

- **Filtrage simple** : Exclut les titres avec genres incompatibles (tout ou rien)
- **Scoring pondéré** : Attribue un score continu, permet un classement et une sélection plus fine

## Notes

- Le modèle nécessite des playlists existantes pour l'entraînement
- Plus il y a de données d'entraînement, meilleur sera le modèle
- Les poids sont sauvegardés et peuvent être réutilisés
- Vous pouvez ré-entraîner le modèle à tout moment pour l'améliorer
