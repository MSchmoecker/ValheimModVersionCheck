import requests

import app_version

default_headers = {
    "Application-Name": "Mod Version Check",
    "Application-Version": str(app_version.app_version)
}


def fetch_online(community: str):
    r = requests.get(f"https://{community}.thunderstore.io/api/v1/package/", headers={**default_headers})
    return r.json()


def download_mod(download_url: str):
    return requests.get(download_url, headers={**default_headers})
