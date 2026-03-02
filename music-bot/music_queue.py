from collections import deque
from dataclasses import dataclass


@dataclass
class Song:
    title: str
    webpage_url: str      # YouTube page URL — always present
    requested_by: str


class MusicQueue:
    def __init__(self):
        self.queue: deque[Song] = deque()
        self.current: Song | None = None
        self.voice_client = None
        self.volume: float = 0.5

    def add(self, song: Song):
        self.queue.append(song)

    def next(self) -> Song | None:
        if self.queue:
            self.current = self.queue.popleft()
            return self.current
        self.current = None
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

    def is_empty(self) -> bool:
        return len(self.queue) == 0

    @property
    def size(self) -> int:
        return len(self.queue)
