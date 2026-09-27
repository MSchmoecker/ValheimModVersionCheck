import datetime
import logging
from typing import List, Tuple

import requests

import app_version
from src.mod import Mod, HEXIUM

BASE_URL = "https://hexium.gg"

default_headers = {
    "Application-Name": "Mod Version Check",
    "Application-Version": app_version.app_version,
}


def fetch_online(community: str) -> Tuple[bool, List[dict]]:
    try:
        r = requests.get(
            f"{BASE_URL}/c/{community}/api/v1/package/", headers={**default_headers}
        )
    except Exception as e:
        logging.exception(f"{HEXIUM} package request failed: {e}")
        return False, []

    if r.status_code == 200:
        return True, r.json()

    logging.info(f"{HEXIUM} package request failed with status code {r.status_code}")
    return False, []


def download_mod(download_url: str) -> requests.Response:
    return requests.get(download_url, headers={**default_headers})


def to_mods(community: str) -> List[Mod]:
    success, packages = fetch_online(community)
    return packages_to_mods(packages)


def parse_date(date: str) -> datetime.datetime:
    return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")


def is_modpack(package: dict) -> bool:
    return (
        "Modpacks" in package["categories"]
        or "modpack" in package["name"].lower()
        or len(package["versions"][0]["dependencies"]) >= 5
    )


def packages_to_mods(packages: List[dict]) -> List[Mod]:
    mods: List[Mod] = []

    for package in packages:
        version = package["versions"][0]

        try:
            mods.append(
                Mod(
                    package["name"],
                    version["version_number"],
                    parse_date(version["date_created"]),
                    package["is_deprecated"],
                    is_modpack(package),
                    HEXIUM,
                    version["icon"],
                    package["package_url"],
                    package["categories"],
                )
            )
        except Exception as e:
            logging.error(f"Error adding mod {package['name']} from {HEXIUM}: {e}")

    return mods
