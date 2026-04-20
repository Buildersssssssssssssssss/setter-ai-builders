import os

import httpx

from nodes.normalize_input import SetterAIState

GRAPH_BASE = "https://graph.instagram.com/v25.0"
PROFILE_FIELDS = "name,username,profile_pic,follower_count,is_verified_user"


def enrich_user(state: SetterAIState) -> dict:
    sender_id = state.get("id_instagram", "")
    if not sender_id:
        return {}

    token = os.environ.get("IG_ACCESS_TOKEN", "")
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{GRAPH_BASE}/{sender_id}",
                params={"fields": PROFILE_FIELDS, "access_token": token},
            )
        data = response.json()

        if "error" in data:
            print(f"[ENRICH_USER] Error de API: {data['error']}")
            return {}

        result = {
            "user_name": data.get("name"),
            "user_username": data.get("username"),
            "user_profile_pic": data.get("profile_pic"),
            "user_follower_count": data.get("follower_count"),
            "user_is_verified": data.get("is_verified_user", False),
        }
        print(f"[ENRICH_USER] {result['user_username']!r} followers={result['user_follower_count']} verified={result['user_is_verified']}")
        return result

    except Exception as e:
        print(f"[ENRICH_USER] Error al obtener perfil: {e}")
        return {}
