from credentials import sp
import re

def find_all_playlists():
    print("[*] Recherche de toutes les playlists (y compris celles avec 'auto')...\n")
    
    playlists = []
    results = sp.current_user_playlists(limit=50)
    
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results.get("next") else None
    
    me = sp.current_user()
    user_id = me["id"]
    
    print(f"Total: {len(playlists)} playlists\n")
    print("=" * 80)
    
    # Chercher avec differentes variations
    auto_keywords = ["auto", "automatic", "generated", "spotify", "daily", "weekly", "discover"]
    auto_playlists = []
    
    for playlist in playlists:
        name = playlist.get("name", "").lower()
        # Chercher si le nom contient un des mots-cles
        if any(keyword in name for keyword in auto_keywords):
            auto_playlists.append(playlist)
    
    if auto_playlists:
        print(f"\n[*] {len(auto_playlists)} playlist(s) suspecte(s) trouvee(s):\n")
        for idx, playlist in enumerate(auto_playlists, 1):
            name = playlist.get("name", "Sans nom")
            owner = playlist.get("owner", {})
            owner_id = owner.get("id", "Inconnu")
            owner_name = owner.get("display_name") or owner_id
            is_owned = owner_id == user_id
            tracks_count = playlist.get("tracks", {}).get("total", 0)
            public = playlist.get("public", False)
            collaborative = playlist.get("collaborative", False)
            
            print(f"{idx}. {name}")
            print(f"   Proprietaire: {owner_name} (ID: {owner_id})")
            print(f"   Votre compte: {'OUI' if is_owned else 'NON'}")
            print(f"   {tracks_count} pistes | {'Public' if public else 'Prive'} | Collaborative: {collaborative}")
            print(f"   ID: {playlist.get('id')}")
            print()
    else:
        print("\n[+] Aucune playlist suspecte trouvee avec les mots-cles: auto, automatic, generated, spotify, daily, weekly, discover")
    
    # Afficher toutes les playlists avec leurs proprietaires pour verification
    print("\n" + "=" * 80)
    print("[*] TOUTES VOS PLAYLISTS (avec details du proprietaire):\n")
    
    for idx, playlist in enumerate(playlists, 1):
        name = playlist.get("name", "Sans nom")
        owner = playlist.get("owner", {})
        owner_id = owner.get("id", "Inconnu")
        owner_name = owner.get("display_name") or owner_id
        is_owned = owner_id == user_id
        
        # Marquer si ce n'est pas votre playlist
        marker = "" if is_owned else " [AUTRE PROPRIETAIRE]"
        print(f"{idx:3d}. {name}{marker}")
        if not is_owned:
            print(f"     Proprietaire: {owner_name} (ID: {owner_id})")

if __name__ == "__main__":
    find_all_playlists()

