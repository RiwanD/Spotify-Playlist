# delete_oct2025_playlists.py
import sys
import time
from datetime import datetime, timezone
from typing import List, Dict

try:
    # Utilise ton module d'authentification existant
    from credentials import sp
except ImportError:
    # Alternative directe si besoin :
    # import spotipy
    # from spotipy.oauth2 import SpotifyOAuth
    # sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    #     client_id=CLIENT_ID,
    #     client_secret=CLIENT_SECRET,
    #     redirect_uri="http://127.0.0.1:8888/callback",
    #     scope="playlist-read-private playlist-modify-public playlist-modify-private"
    # ))
    raise RuntimeError("Import de `credentials` impossible. Assure-toi que credentials.py est présent.")

OCT_START = datetime(2025, 10, 1, tzinfo=timezone.utc)
NOV_START = datetime(2025, 11, 1, tzinfo=timezone.utc)

def is_oct_2025(dt: datetime) -> bool:
    return OCT_START <= dt < NOV_START

def get_all_user_playlists() -> List[Dict]:
    print("[*] Recuperation des playlists...")
    playlists = []
    results = sp.current_user_playlists(limit=50)
    while results:
        playlists.extend(results["items"])
        print(f"  -> {len(playlists)} playlists chargees...")
        results = sp.next(results) if results.get("next") else None
        time.sleep(0.1)  # anti rate-limit
    return playlists

def earliest_track_date(playlist_id: str) -> datetime | None:
    """
    Retourne la plus ancienne date 'added_at' parmi les titres de la playlist.
    None si playlist vide (ou non accessible).
    """
    earliest = None
    results = sp.playlist_items(playlist_id, fields="items(added_at),next", limit=100)
    while results:
        for it in results.get("items", []):
            added = it.get("added_at")
            if added:
                try:
                    dt = datetime.fromisoformat(added.replace("Z", "+00:00"))
                    if earliest is None or dt < earliest:
                        earliest = dt
                except Exception:
                    pass
        results = sp.next(results) if results.get("next") else None
        time.sleep(0.1)
    return earliest

def delete_playlists(confirm=False, auto_mode=False):
    """
    Supprime des playlists selon les critères spécifiés.
    
    Args:
        confirm: Si True, supprime réellement les playlists. Si False, mode dry-run.
        auto_mode: Si True, cible les playlists contenant '(auto)'. Si False, cible les playlists d'octobre 2025.
    """
    me = sp.current_user()
    user_id = me["id"]
    print(f"[*] Connecte en tant que {me.get('display_name') or user_id} ({user_id})")
    
    if auto_mode:
        print("[*] Cible : playlists contenant '(auto)' dans le nom")
    else:
        print("[*] Cible : playlists creees (premiere date d'ajout) en octobre 2025")

    playlists = get_all_user_playlists()

    # Filtrer : playlists dont tu es propriétaire (évite d'unfollow des playlists suivies d'autrui)
    owned = [p for p in playlists if p.get("owner", {}).get("id") == user_id]
    print(f"[*] Playlists dont tu es propriétaire : {len(owned)}")

    candidates = []
    for idx, p in enumerate(owned, start=1):
        pid = p["id"]
        name = p.get("name", "Sans nom")
        print(f"  [{idx}/{len(owned)}] Inspection: {name}")
        
        if auto_mode:
            # Mode auto : chercher les playlists avec "(auto)" dans le nom
            if "(auto)" in name.lower():
                candidates.append((pid, name, None))
                print(f"     [+] CANDIDATE (contient '(auto)')")
            else:
                print(f"     [-] Ne contient pas '(auto)'")
        else:
            # Mode octobre 2025 : chercher par date
            first_dt = earliest_track_date(pid)
            if first_dt is None:
                # Playlist vide : impossible de dater → on ignore par sécurité
                print("     [i] Playlist vide ou non datable -> ignoree")
                continue
            if is_oct_2025(first_dt):
                candidates.append((pid, name, first_dt))
                print(f"     [+] CANDIDATE (premier ajout : {first_dt.isoformat()})")
            else:
                print(f"     [-] Hors cible (premier ajout : {first_dt.isoformat()})")

    if not candidates:
        if auto_mode:
            print("\n[+] Aucune playlist contenant '(auto)' trouvee.")
        else:
            print("\n[+] Aucune playlist a supprimer pour octobre 2025 selon ce critere.")
        return

    print("\n[*] PLAYLISTS CIBLEES (suppression = unfollow) :")
    for pid, name, dt in candidates:
        if dt:
            print(f"  • {name} — {dt:%Y-%m-%d %H:%M UTC} — id: {pid}")
        else:
            print(f"  • {name} — id: {pid}")

    if not confirm:
        print("\n[?] Aucune suppression effectuee (dry-run).")
        if auto_mode:
            print("   -> Relance avec l'option :  python main.py --delete --auto --confirm")
        else:
            print("   -> Relance avec l'option :  python main.py --delete --confirm")
        return

    print("\n[*] Suppression (unfollow) en cours...")
    for pid, name, dt in candidates:
        sp.current_user_unfollow_playlist(pid)
        print(f"  [+] Supprimee de ton compte : {name}")
        time.sleep(0.15)

    print("\n[+] Termine.")


def main():
    """Fonction main pour exécution directe du script."""
    confirm = ("--confirm" in sys.argv)
    auto_mode = ("--auto" in sys.argv)
    delete_playlists(confirm=confirm, auto_mode=auto_mode)

if __name__ == "__main__":
    main()
