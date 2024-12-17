import os.path
import random
from typing import Optional


class DialogRenderer:
    def __init__(self, directory: Optional[str] = None):
        self.directory = directory

    def get_dialog(self, name: str) -> str:
        if not self.directory:
            return name
        path = os.path.join(self.directory, name + ".dialog")
        with open(path) as f:
            lines = [l for l in f.read().split("\n")
                     if l and not l.startswith("# ")]
        return random.choice(lines)

    def get_text(self, name: str) -> str:
        if not self.directory:
            return name
        path = os.path.join(self.directory, name + ".txt")
        with open(path) as f:
            return f.read()