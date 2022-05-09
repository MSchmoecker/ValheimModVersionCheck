import requests


def fetch_online():
    r = requests.get("https://valheim.thunderstore.io/api/v1/package/")
    return r.json()
