import requests

APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
TIMEOUT = 5
STORESEARCH_URL = "https://store.steampowered.com/api/storesearch/"
HEADER_URL = "https://cdn.akamai.steamstatic.com/steam/apps/{}/header.jpg"
MAX_RESULTS = 8
COUNTRY = "ua"
LANGUAGE = "ukrainian"


def search_games(term):
    try:
        response = requests.get(
            STORESEARCH_URL,
            params={"term": term, "l": LANGUAGE, "cc": COUNTRY},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except (requests.RequestException, ValueError):
        raise SteamUnavailableError()

    return [
        {"steam_id": item["id"], "title": item["name"], "img_url": HEADER_URL.format(item["id"])}
        for item in items
        if item.get("type") == "app"
    ][:MAX_RESULTS]


def fetch_app_details(steam_id):
    try:
        response = requests.get(
            APPDETAILS_URL,
            params={"appids": steam_id, "l": LANGUAGE, "cc": COUNTRY},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        raise SteamUnavailableError()

    entry = payload.get(str(steam_id), {})
    if not entry.get("success"):
        return None
    data = entry["data"]

    price = data.get("price_overview") or {}
    return {
        "name": data.get("name"),
        "short_description": data.get("short_description"),
        "header_image": data.get("header_image"),
        "is_free": data.get("is_free", False),
        "price": price.get("final_formatted"),
        "discount_percent": price.get("discount_percent", 0),
        "store_url": f"https://store.steampowered.com/app/{steam_id}",
    }
