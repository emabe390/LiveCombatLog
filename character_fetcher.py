import datetime
import json
import os
import threading
from multiprocessing import Pool

import requests

import version

CACHE_DIR = "cache"
IMAGES_DIR = "images"
CHARACTER_JSON = "characters.json"

ID_KEY = "id"
TIMEOUT_KEY = "timeout"
THREAD_KEY = "thread"
ERROR_FETCHING_KEY = "error_fetching_data"
CHARACTERS_KEY = "characters"
VERSION_KEY = "version"

DATA_KEYS = {ERROR_FETCHING_KEY}

CACHE = None


class Cache:
    @staticmethod
    def get_instance():
        # TODO : actual singleton
        global CACHE
        if CACHE is None:
            CACHE = Cache()
        return CACHE

    def __init__(self):
        self.data = None
        if os.path.exists(f"{CACHE_DIR}/{CHARACTER_JSON}"):
            with open(f"{CACHE_DIR}/{CHARACTER_JSON}", "r") as file:
                self.data = json.load(file)
            if self.data["version"] < version.VERSION:
                print(f"Older version of cache exists in {CACHE_DIR}, clearing data...")
                self.data = None
        if self.data is None:
            self.data = {CHARACTERS_KEY: {},
                         VERSION_KEY: version.VERSION}
        self.temp_data = {}
        self.pool = Pool(processes=5)
        self.errors = set()
        if ERROR_FETCHING_KEY in self.data:
            self.errors = set(self.data[ERROR_FETCHING_KEY])

    def save(self):
        self.data[ERROR_FETCHING_KEY] = sorted(self.errors)
        with open(f"{CACHE_DIR}/{CHARACTER_JSON}", "w") as file:
            json.dump(self.data, file, indent=2)

    def get_images(self, *users):
        self.get_missing(users)

        for user in users:
            if user in DATA_KEYS:
                continue
            user_id = self.data[CHARACTERS_KEY][user][ID_KEY]
            if image_exists(user_id):
                continue
            self.download_image(user_id)

    def get_temp_data(self, user_id, key):
        if user_id in self.temp_data:
            if key in self.temp_data[user_id]:
                return self.temp_data[user_id][key]
        return None

    def set_temp_data(self, user_id, key, value):
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        self.temp_data[user_id][key] = value

    def wait_for_image(self, user_id):
        if user_id in self.temp_data and THREAD_KEY in self.temp_data[user_id]:
            self.temp_data[user_id][THREAD_KEY].get()

    def download_image(self, user_id):
        thread = self.get_temp_data(user_id, THREAD_KEY)
        if thread is None:
            thread = self.pool.apply_async(fetch_data, args=(user_id,))
            self.set_temp_data(user_id, THREAD_KEY, thread)

    def download_all_images(self):
        self.get_images(*list(self.data[CHARACTERS_KEY].keys()))
        for name in self.data[CHARACTERS_KEY]:
            if name not in DATA_KEYS:
                self.wait_for_image(self.data[CHARACTERS_KEY][name][ID_KEY])

    def wait_for_threads(self):
        for key in self.temp_data:
            if THREAD_KEY in self.temp_data[key]:
                self.temp_data[key][THREAD_KEY].get()

    def get_missing(self, *users):
        # print(users)

        missing = set(*users) - set(self.data[CHARACTERS_KEY].keys()) - self.errors
        missing = [x for x in missing if not x.startswith("Wreck of: ")]

        for x in missing:
            if len(x) != len(x.strip()):
                raise IndexError

        if missing:
            headers = {
                "accept": "application/json",
                "Accept-Language": "en",
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            }
            data = "[\"" + "\", \"".join(missing) + "\"]"

            r = requests.post(r"https://esi.evetech.net/latest/universe/ids/?datasource=tranquility&language=en",
                              headers=headers, data=data)

            if r.status_code != 200:
                print("Could not fetch id's for users: " + data)
                return

            parsed = r.json()

            if "characters" not in parsed:
                self.errors = self.errors.union(set(*users))
                print(f"Could not fetch id's for users: {users}")
                return

            for data in r.json()["characters"]:
                self.data[CHARACTERS_KEY][data["name"]] = {ID_KEY: data["id"],
                                           TIMEOUT_KEY: (datetime.datetime.now() + datetime.timedelta(
                                               hours=72)).isoformat()}


def get_image_url(user_id):
    headers = {
        "accept": "application/json",
        "Accept-Language": "en",
    }

    print("<<<<<<<<<<" + f"https://esi.evetech.net/latest/characters/{user_id}/portrait/")
    resp = requests.get(f"https://esi.evetech.net/latest/characters/{user_id}/portrait/", headers=headers)

    if resp.status_code == 200:
        return resp.json()["px64x64"]


def image_exists(user_id):
    return os.path.exists(f"{CACHE_DIR}/{IMAGES_DIR}/{user_id}.png")


def fetch_data(user_id):
    path = f"{CACHE_DIR}/{IMAGES_DIR}/{user_id}.png"
    if not image_exists(user_id):
        print(f"Downloading {user_id}.png")
        url = get_image_url(user_id)
        if url is None:
            print(f"Could not get url for {user_id}")
            return
        resp = requests.get(url)
        if resp.status_code == 200:
            with open(path, "wb") as file:
                file.write(resp.content)
        else:
            print(f"Error downloading {id}")


if __name__ == "__main__":
    cache = Cache()
    cache.get_images("Freany", "Emely Rados", "Karl Egosa", "Kalder Okanata")
    cache.save()
