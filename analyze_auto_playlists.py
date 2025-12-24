from credentials import sp
from datetime import datetime, timezone

def analyze_auto_playlists():
    print("[*] Recherche des playlists contenant '(auto)'...\n")
    
    playlists = []
    results = sp.current_user_playlists(limit=50)
    
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results.get("next") else None
    
    me = sp.current_user()
    user_id = me["id"]
    
    # Filtrer les playlists avec "(auto)"
    auto_playlists = [p for p in playlists if "(auto)" in p.get("name", "").lower()]
    
    if not auto_playlists:
        print("[+] Aucune playlist contenant '(auto)' trouvee.")
        return
    
    print(f"[*] {len(auto_playlists)} playlist(s) contenant '(auto)' trouvee(s):\n")
    print("=" * 80)
    
    for idx, playlist in enumerate(auto_playlists, 1):
        name = playlist.get("name", "Sans nom")
        playlist_id = playlist.get("id")
        owner = playlist.get("owner", {})
        owner_id = owner.get("id", "Inconnu")
        owner_name = owner.get("display_name") or owner_id
        is_owned = owner_id == user_id
        tracks_count = playlist.get("tracks", {}).get("total", 0)
        public = "Public" if playlist.get("public") else "Prive"
        collaborative = playlist.get("collaborative", False)
        created_at = playlist.get("created_at")
        
        print(f"\n{idx}. {name}")
        print(f"   ID: {playlist_id}")
        print(f"   Proprietaire: {owner_name} (ID: {owner_id})")
        print(f"   Votre playlist: {'OUI' if is_owned else 'NON'}")
        print(f"   {tracks_count} pistes | {public} | Collaborative: {collaborative}")
        if created_at:
            print(f"   Date de creation (API): {created_at}")
        
        # Essayer de trouver la date du premier titre ajoute
        print(f"   Analyse des pistes...")
        try:
            results = sp.playlist_items(playlist_id, fields="items(added_at),next", limit=100)
            earliest = None
            latest = None
            total_checked = 0
            
            while results:
                for item in results.get("items", []):
                    added = item.get("added_at")
                    if added:
                        try:
                            dt = datetime.fromisoformat(added.replace("Z", "+00:00"))
                            if earliest is None or dt < earliest:
                                earliest = dt
                            if latest is None or dt > latest:
                                latest = dt
                            total_checked += 1
                        except Exception:
                            pass
                results = sp.next(results) if results.get("next") else None
            
            if earliest:
                print(f"   Premier titre ajoute: {earliest.isoformat()}")
            if latest:
                print(f"   Dernier titre ajoute: {latest.isoformat()}")
            print(f"   {total_checked} pistes analysees")
        except Exception as e:
            print(f"   Erreur lors de l'analyse: {e}")
        
        # Obtenir plus de details sur la playlist
        try:
            full_playlist = sp.playlist(playlist_id)
            description = full_playlist.get("description", "")
            if description:
                print(f"   Description: {description}")
            followers = full_playlist.get("followers", {}).get("total", 0)
            print(f"   Abonnes: {followers}")
        except Exception as e:
            print(f"   Erreur lors de la recuperation des details: {e}")
        
        print("-" * 80)
    
    print(f"\n[*] Analyse terminee.")

if __name__ == "__main__":
    analyze_auto_playlists()

