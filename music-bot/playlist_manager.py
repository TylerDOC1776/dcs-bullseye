import json
import os


PLAYLISTS_FILE = 'playlists.json'


class PlaylistManager:
    def __init__(self, filepath: str = PLAYLISTS_FILE):
        self.filepath = filepath
        self._data: dict = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self._data = json.load(f)

    def _save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _user(self, user_id: int) -> dict:
        return self._data.setdefault(str(user_id), {})

    def create(self, user_id: int, name: str) -> bool:
        user = self._user(user_id)
        if name in user:
            return False
        user[name] = []
        self._save()
        return True

    def delete(self, user_id: int, name: str) -> bool:
        user = self._user(user_id)
        if name not in user:
            return False
        del user[name]
        self._save()
        return True

    def add_song(self, user_id: int, playlist: str, title: str, webpage_url: str) -> bool:
        user = self._user(user_id)
        if playlist not in user:
            return False
        user[playlist].append({'title': title, 'webpage_url': webpage_url})
        self._save()
        return True

    def remove_song(self, user_id: int, playlist: str, index: int) -> bool:
        user = self._user(user_id)
        if playlist not in user:
            return False
        songs = user[playlist]
        if not 0 <= index < len(songs):
            return False
        songs.pop(index)
        self._save()
        return True

    def get(self, user_id: int, name: str) -> list | None:
        return self._user(user_id).get(name)

    def all_playlists(self, user_id: int) -> dict:
        return self._user(user_id)
