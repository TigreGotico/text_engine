import os.path
import random
from typing import Optional

from text_engine.utils import load_template_file


class DialogRenderer:
    def __init__(self, directory: Optional[str] = None):
        self.directory = directory

    def get_dialog(self, name: str) -> str:
        """returns a random line from a dialog file"""
        if not self.directory:
            return name
        path = os.path.join(self.directory, name + ".dialog")
        lines = load_template_file(path)
        return random.choice(lines)

    def get_text(self, name: str) -> str:
        """sometimes we need to load a full text file, not line by line"""
        if not self.directory:
            return name
        path = os.path.join(self.directory, name + ".txt")
        with open(path) as f:
            return f.read()
