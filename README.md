# Spotify-Playlist

Application Python pour créer et gérer des playlists Spotify automatiquement selon les genres musicaux, en utilisant la nomenclature française de classification des genres musicaux.

## Description

Cette application permet de :
- Créer automatiquement des playlists organisées par classe de genres musicaux selon la nomenclature française
- Analyser et gérer vos playlists existantes
- Identifier et supprimer des playlists automatiques

## Configuration

### Création de ID_client.txt

Vous devez créer un fichier `ID_client.txt` dans le même dossier que `credentials.py`.

Structure du fichier :
```
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
```

### Installation des dépendances

```bash
pip install spotipy
```

## Structure du projet

- `main.py` : Script principal qui route vers les différentes fonctionnalités
- `music_genre.py` : Gestion de la création de playlists par classe selon la nomenclature française
- `credentials.py` : Gestion de l'authentification Spotify
- `genres/` : Dossier contenant les fichiers JSON de classification des genres (nomenclature française)
  - `classe_0.json` à `classe_9.json` : Fichiers de classification par classe
- `analyze_auto_playlists.py` : Analyse des playlists contenant '(auto)'
- `find_auto_playlists.py` : Recherche de playlists suspectes
- `list_playlists.py` : Liste toutes vos playlists
- `check_auto_created.py` : Vérifie les playlists créées automatiquement
- `delete_playlist.py` : Suppression de playlists

## Fonctionnalités

### 1. Création de playlists par classe (par défaut)

Crée des playlists organisées selon la nomenclature française des genres musicaux. Chaque playlist correspond à une classe (ex: "musiques d'influence afro-américaine", "musique classique", etc.) et contient toutes les chansons likées correspondant aux genres de cette classe.

**Usage :**
```bash
python main.py                    # Mode dry-run (affiche ce qui serait créé)
python main.py --confirm           # Crée réellement les playlists
```

### 2. Analyse des playlists auto

Analyse en détail toutes les playlists contenant '(auto)' dans leur nom, avec informations sur les dates de création, nombre de pistes, etc.

**Usage :**
```bash
python main.py --analyze
```

### 3. Recherche de playlists suspectes

Trouve toutes les playlists suspectes (contenant des mots-clés comme "auto", "automatic", "generated", "spotify", "daily", "weekly", "discover") et affiche toutes vos playlists avec leurs propriétaires.

**Usage :**
```bash
python main.py --find
```

### 4. Liste de toutes les playlists

Affiche la liste complète de toutes vos playlists avec leurs informations (nombre de pistes, visibilité, propriétaire).

**Usage :**
```bash
python main.py --list
```

### 5. Vérification des playlists auto

Vérifie les playlists créées automatiquement par le script (contenant '(auto)' ou 'Mix' dans le nom).

**Usage :**
```bash
python main.py --check
```

### 6. Suppression de playlists

Permet de supprimer (unfollow) des playlists selon différents critères :
- Mode `--auto` : Cible les playlists contenant '(auto)' dans le nom
- Sans `--auto` : Cible les playlists créées en octobre 2025 (par date du premier titre ajouté)

**Usage :**
```bash
python main.py --delete --auto              # Dry-run : supprimer les playlists '(auto)'
python main.py --delete --auto --confirm    # Supprimer réellement les playlists '(auto)'
python main.py --delete --confirm           # Supprimer les playlists d'octobre 2025
```

### 7. Aide

Affiche l'aide avec toutes les options disponibles.

**Usage :**
```bash
python main.py --help
# ou
python main.py -h
```

## Utilisation complète

### Exemple de workflow typique

1. **Créer les playlists par classe (dry-run) :**
   ```bash
   python main.py
   ```

2. **Créer réellement les playlists :**
   ```bash
   python main.py --confirm
   ```

3. **Vérifier les playlists créées :**
   ```bash
   python main.py --check
   ```

4. **Analyser les playlists auto :**
   ```bash
   python main.py --analyze
   ```

5. **Supprimer les anciennes playlists auto (dry-run) :**
   ```bash
   python main.py --delete --auto
   ```

6. **Supprimer réellement :**
   ```bash
   python main.py --delete --auto --confirm
   ```

## Organisation des playlists dans Spotify

### Structure des noms de playlists

Les playlists sont nommées avec des préfixes pour faciliter l'organisation :

- **Playlists par classe** : `{class_label} (auto)` (ex: "musiques d'influence afro-américaine (auto)")
- **Playlists par sous-genre** : `[{class_code}] {bucket_label} (auto)` (ex: "[1] Blues (auto)", "[2] Rock (auto)")

Le préfixe `[X]` permet de regrouper visuellement les playlists de sous-genre par classe dans Spotify.

### Création de dossiers dans Spotify

**Important** : L'API Spotify ne permet pas de créer des dossiers de playlists. Vous devez les créer manuellement dans l'interface Spotify, puis y déplacer les playlists.

**Comment créer un dossier et y organiser les playlists :**

1. **Ouvrir Spotify** sur votre ordinateur (application de bureau ou lecteur web)
2. **Accéder à votre Bibliothèque** (section "Playlists")
3. **Créer un dossier** :
   - Cliquez sur l'icône **"+"** (Plus) en haut
   - Sélectionnez **"Créer un dossier de playlists"**
   - Nommez-le selon la classe (ex: "Classe 1 - Musiques afro-américaines")
4. **Déplacer les playlists dans le dossier** :
   - Glissez-déposez les playlists avec le préfixe `[X]` dans le dossier correspondant
   - Ou cliquez sur les trois points `...` d'une playlist → **"Ajouter au dossier"**

**Exemple d'organisation recommandée :**

```
📁 Classe 1 - Musiques d'influence afro-américaine
  ├── [1] Blues (auto)
  ├── [1] Jazz (auto)
  ├── [1] R&B, Soul, Disco/Funk (auto)
  ├── [1] Hip hop, Rap (auto)
  └── [1] Reggae, Ska, Dancehall, Dub (auto)

📁 Classe 2 - Rock et variétés
  ├── [2] Rock (auto)
  ├── [2] Pop (auto)
  ├── [2] Hard Rock / Metal (auto)
  └── ...
```

Les playlists principales par classe peuvent rester à la racine ou être placées dans un dossier "Playlists principales".

## Notes importantes

- **Mode dry-run** : Par défaut, les actions de création/suppression sont en mode dry-run. Utilisez `--confirm` pour exécuter réellement les actions.
- **Nomenclature française** : Le dossier `genres/` contient les fichiers de classification basés sur la nomenclature française des genres musicaux (PCDM).
- **Limite API** : Les playlists sont limitées à 1000 morceaux (limitation de l'API Spotify).
- **Rate limiting** : Le script inclut des délais pour éviter de dépasser les limites de l'API Spotify.
- **Dossiers Spotify** : Les dossiers doivent être créés manuellement dans l'interface Spotify. Le préfixe `[X]` facilite l'identification et le regroupement des playlists.

## À faire

- Changer la manière dont les catégories sont faites, en genre plus général et pas en sous genre, à partir du fichier csv récupéré et de la conversation précédente.  
