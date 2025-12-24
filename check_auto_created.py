from credentials import sp

def check_auto_playlists():
    print("[*] Recherche des playlists creees par main.py (avec '(auto)')...\n")
    
    playlists = []
    results = sp.current_user_playlists(limit=50)
    
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results.get("next") else None
    
    me = sp.current_user()
    user_id = me["id"]
    
    # Chercher les playlists avec "(auto)" ou "Mix" dans le nom
    auto_playlists = [p for p in playlists if "(auto)" in p.get("name", "").lower() or "mix" in p.get("name", "").lower()]
    
    if auto_playlists:
        print(f"[*] {len(auto_playlists)} playlist(s) avec '(auto)' ou 'Mix' trouvee(s):\n")
        print("=" * 80)
        
        for idx, playlist in enumerate(auto_playlists, 1):
            name = playlist.get("name", "Sans nom")
            playlist_id = playlist.get("id")
            owner = playlist.get("owner", {})
            owner_id = owner.get("id", "Inconnu")
            is_owned = owner_id == user_id
            tracks_count = playlist.get("tracks", {}).get("total", 0)
            public = "Public" if playlist.get("public") else "Prive"
            
            print(f"{idx}. {name}")
            print(f"   ID: {playlist_id}")
            print(f"   Proprietaire: Vous (ID: {owner_id})" if is_owned else f"   Proprietaire: {owner_id}")
            print(f"   {tracks_count} pistes | {public}")
            
            # Obtenir la description
            try:
                full_playlist = sp.playlist(playlist_id)
                description = full_playlist.get("description", "")
                if description:
                    print(f"   Description: {description}")
            except:
                pass
            print()
    else:
        print("[+] Aucune playlist avec '(auto)' ou 'Mix' trouvee actuellement.")
        print("\n[*] Cela signifie soit:")
        print("    1. Le script main.py n'a pas encore ete execute")
        print("    2. Les playlists ont ete supprimees")
        print("    3. Elles sont privees et ne sont pas dans cette liste")
    
    print("\n" + "=" * 80)
    print("[*] Explication:")
    print("    Le script main.py cree automatiquement des playlists avec '(auto)'")
    print("    dans le nom. Ces playlists sont bien creees par VOTRE compte,")
    print("    mais de maniere automatique par le script.")
    print("    C'est normal qu'elles apparaissent comme creees par vous!")

if __name__ == "__main__":
    check_auto_playlists()

