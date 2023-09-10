import requests


def fetch_online(community: str):
    r = requests.get(f"https://{community}.thunderstore.io/api/v1/package/")
    return r.json()
