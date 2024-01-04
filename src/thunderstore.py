import requests
import logging

import app_version

default_headers = {
    "Application-Name": "Mod Version Check",
    "Application-Version": str(app_version.app_version)
}


def fetch_online(community: str):
    r = requests.get(f"https://{community}.thunderstore.io/api/v1/package/", headers={**default_headers})

    if r.status_code == 200:
        return True, r.json()

    logging.info(f"Thunderstore package request failed with status code {r.status_code}")
    return False, []


def download_mod(download_url: str):
    return requests.get(download_url, headers={**default_headers})
