import datetime
import requests

last_online_fetched: datetime = None
mods_online: dict = {}


def parse_created_date(target):
    return datetime.datetime.strptime(target["date_created"], "%Y-%m-%dT%H:%M:%S.%fZ")


def fetch_online():
    global last_online_fetched, mods_online

    if last_online_fetched is None or last_online_fetched < datetime.datetime.now() - datetime.timedelta(minutes=1):
        print("Fetch Thunderstore ... ", end="")
        mods_online = _fetch_online()
        print("done")
        last_online_fetched = datetime.datetime.now()

    return mods_online


def _fetch_online():
    r = requests.get("https://valheim.thunderstore.io/api/v1/package/")
    return r.json()
