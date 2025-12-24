from credentials import sp

def list_all_playlists():
    print("[*] Recuperation de toutes vos playlists...\n")
    
    playlists = []
    results = sp.current_user_playlists(limit=50)
    
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results.get("next") else None
    
    me = sp.current_user()
    user_id = me["id"]
    
    print(f"Total: {len(playlists)} playlists\n")
    print("-" * 80)
    
    for idx, playlist in enumerate(playlists, 1):
        name = playlist.get("name", "Sans nom")
        owner = playlist.get("owner", {}).get("display_name") or playlist.get("owner", {}).get("id", "Inconnu")
        is_owned = playlist.get("owner", {}).get("id") == user_id
        tracks_count = playlist.get("tracks", {}).get("total", 0)
        public = "Public" if playlist.get("public") else "Prive"
        owned_status = "(Votre)" if is_owned else f"(Par: {owner})"
        
        print(f"{idx:3d}. {name}")
        print(f"     {tracks_count} pistes | {public} | {owned_status}")
        print(f"     ID: {playlist.get('id')}")
        print()

if __name__ == "__main__":
    list_all_playlists()

