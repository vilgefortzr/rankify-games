import html

import requests

from .exception_handler import SteamUnavailableError

APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
TIMEOUT = 5
STORESEARCH_URL = "https://store.steampowered.com/api/storesearch/"
HEADER_URL = "https://cdn.akamai.steamstatic.com/steam/apps/{}/header.jpg"
MAX_RESULTS = 8
MAX_SCREENSHOTS = 6
COUNTRY = "ua"
FALLBACK_COUNTRY = "us"
LANGUAGE = "english"


def _get_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise SteamUnavailableError() from exc

    if not isinstance(payload, dict):
        raise SteamUnavailableError()
    return payload


def _available_ids(ids, country):
    if not ids:
        return set()
    payload = _get_json(
        APPDETAILS_URL,
        {
            "appids": ",".join(map(str, ids)),
            "filters": "price_overview",
            "cc": country,
        },
    )
    return {int(app_id) for app_id, entry in payload.items() if entry.get("success")}


def search_games(term):
    payload = _get_json(STORESEARCH_URL, {"term": term, "l": LANGUAGE, "cc": COUNTRY})
    items = [item for item in payload.get("items", []) if item.get("type") == "app"]

    ids = [item["id"] for item in items]
    available = _available_ids(ids, COUNTRY)
    available.update(
        _available_ids([i for i in ids if i not in available], FALLBACK_COUNTRY)
    )

    return [
        {
            "steam_id": item["id"],
            "title": item["name"],
            "img_url": HEADER_URL.format(item["id"]),
        }
        for item in items
        if item["id"] in available
    ][:MAX_RESULTS]


def _fetch_app_data(steam_id, country):
    payload = _get_json(
        APPDETAILS_URL, {"appids": steam_id, "l": LANGUAGE, "cc": country}
    )
    entry = payload.get(str(steam_id), {})
    return entry.get("data") if entry.get("success") else None


def _fetch_app_data_with_fallback(steam_id):
    return _fetch_app_data(steam_id, COUNTRY) or _fetch_app_data(
        steam_id, FALLBACK_COUNTRY
    )


def fetch_game(steam_id):
    data = _fetch_app_data_with_fallback(steam_id)
    if data is None:
        return None
    return {
        "title": data.get("name") or "",
        "img_url": data.get("header_image") or HEADER_URL.format(steam_id),
    }


def fetch_app_details(steam_id):
    data = _fetch_app_data_with_fallback(steam_id)
    if data is None:
        return None

    release = data.get("release_date") or {}
    metacritic = data.get("metacritic") or {}
    description = data.get("short_description")
    screenshots = [
        {"thumbnail": shot.get("path_thumbnail"), "full": shot["path_full"]}
        for shot in data.get("screenshots") or []
        if shot.get("path_full")
    ][:MAX_SCREENSHOTS]

    return {
        "short_description": html.unescape(description) if description else None,
        "background_url": data.get("background_raw") or data.get("background"),
        "screenshots": screenshots,
        "release_date": release.get("date"),
        "coming_soon": release.get("coming_soon", False),
        "developers": data.get("developers") or [],
        "publishers": data.get("publishers") or [],
        "genres": [
            genre["description"]
            for genre in data.get("genres") or []
            if genre.get("description")
        ],
        "metacritic_score": metacritic.get("score"),
        "store_url": f"https://store.steampowered.com/app/{steam_id}",
    }
