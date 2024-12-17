import os.path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Callable

from json_database import JsonStorage
from text_engine.utils import load_template_file

DEBUG = False  # just a helper during development

# Type alias for intent handler functions
IntentHandler = Callable[['IFGameEngine', str], str]


@dataclass
class Keyword:
    """
    Represents a keyword with associated sample phrases for matching.
    """
    name: str
    samples: Optional[List[str]] = None

    def __post_init__(self):
        self.samples = self.samples or [self.name]

    @property
    def file_path(self) -> str:
        """
        Get the file path where the keyword is saved.
        """
        return os.path.join("keywords", f"{self.name}.voc")

    def save(self, directory: str) -> None:
        """
        Save the keyword samples to a file in the specified directory.
        """
        path = os.path.join(directory, self.file_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("\n".join(self.samples))
        if DEBUG:
            print(f"   - DEBUG: saved keyword to file: {self.name} / {path}")

    @classmethod
    def from_file(cls, path: str) -> 'Keyword':
        """
        Load a keyword from a file.
        """
        name = os.path.basename(path).split(".voc")[0]
        samples = load_template_file(path)
        if DEBUG:
            print(f"   - DEBUG: loaded keyword from file: {name} / {samples}")
        return cls(name=name, samples=samples)

    def reload(self, directory: str) -> None:
        """
        Reload the keyword samples from its file.
        """
        path = os.path.join(directory, self.file_path)
        if os.path.isfile(path):
            self.name = os.path.basename(path).split(".voc")[0]
            self.samples = load_template_file(path)

    def match(self, utterance: str) -> bool:
        """
        Check if any sample in the keyword matches the given utterance.
        """
        return any(sample.lower() in utterance.lower() for sample in self.samples)


@dataclass
class KeywordIntent:
    """
    Represents an intent defined by required, optional, and excluded keywords.
    """
    name: str
    required: List[Keyword]
    optional: Optional[List[Keyword]] = None
    excludes: Optional[List[Keyword]] = None
    handler: Optional[IntentHandler] = None

    def __post_init__(self):
        self.optional = self.optional or []
        self.excludes = self.excludes or []

    @property
    def file_path(self) -> str:
        """
        Get the file path where the intent is saved.
        """
        return os.path.join("intents", f"{self.name}.json")

    def save(self, directory: str) -> None:
        """
        Save the intent and its associated keywords to files.
        """
        path = os.path.join(directory, self.file_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        db = JsonStorage(path)
        db["name"] = self.name
        db["required"] = [k.name for k in self.required]
        db["optional"] = [k.name for k in self.optional]
        db["excludes"] = [k.name for k in self.excludes]
        db.store()
        if DEBUG:
            print(f"   - DEBUG: saved intent to file: {self.name} / {path}")
        for kw in self.required + self.optional + self.excludes:
            kw.save(directory)

    @classmethod
    def from_file(cls, path: str) -> 'KeywordIntent':
        """
        Load an intent from a file.
        """
        db = JsonStorage(path)
        required = [Keyword(name) for name in db["required"]]
        optional = [Keyword(name) for name in db["optional"]]
        excludes = [Keyword(name) for name in db["excludes"]]
        intent = cls(name=db["name"], required=required, optional=optional, excludes=excludes)
        if DEBUG:
            print(f"   - DEBUG: loaded intent from file: {intent.name} / {db}")
        directory = os.path.dirname(os.path.dirname(path))
        for k in intent.required + intent.excludes + intent.optional:
            k.reload(directory=directory)
        return intent

    def reload(self, directory: str) -> None:
        """
        Reload the intent and its associated keywords from files.
        """
        path = os.path.join(directory, self.file_path)
        if os.path.isfile(path):
            db = JsonStorage(path)
            self.name = db["name"]
            self.required = [Keyword(name) for name in db["required"]]
            self.optional = [Keyword(name) for name in db["optional"]]
            self.excludes = [Keyword(name) for name in db["excludes"]]
            for kw in self.required + self.optional + self.excludes:
                kw.reload(directory)

    def score(self, utterance: str) -> float:
        """
        Calculate a confidence score for matching the given utterance with the intent.
        """
        if any(k.match(utterance) for k in self.excludes):
            return 0.0

        matched_required = sum(1 for k in self.required if k.match(utterance))
        matched_optional = sum(1 for k in self.optional if k.match(utterance))

        if matched_required < len(self.required):
            return 0.0

        optional_score = matched_optional / len(self.optional) if self.optional else 0
        return max(0.8 + 0.2 * optional_score, 0.5)


class IntentEngine:
    """
    Engine for managing and scoring intents.
    """

    def __init__(self, intent_cache: Optional[str] = None):
        self.intents: Dict[str, KeywordIntent] = {}
        self.cache = intent_cache
        if self.cache:
            intents_path = os.path.join(self.cache, "intents")
            if os.path.isdir(intents_path):
                for fname in os.listdir(intents_path):
                    if fname.endswith(".json"):
                        intent = KeywordIntent.from_file(os.path.join(intents_path, fname))
                        self.intents[intent.name] = intent

    def calc_intents(self, utterance: str) -> List[Tuple[KeywordIntent, float]]:
        """
        Calculate matching intents and their scores for the given utterance.
        """
        return sorted(
            [(intent, intent.score(utterance))
            for intent in self.intents.values()
            if intent.score(utterance) >= 0.5],
            key=lambda item: item[1],
            reverse=True,
        )

    def register_intent(self, intent: KeywordIntent) -> None:
        """
        Register a new intent in the engine.
        """
        self.intents[intent.name] = intent
        if DEBUG:
            print(f"   - DEBUG: registering intent: {intent.name}")

    def deregister_intent(self, name: str) -> None:
        """
        Deregister an intent by name.
        """
        if name in self.intents:
            intent = self.intents.pop(name)
            if self.cache:
                path = os.path.join(self.cache, intent.file_path)
                if os.path.isfile(path):
                    os.remove(path)


class BuiltinKeywords:
    """
    Handles built-in keywords for a specific language.
    """

    def __init__(self, lang: str):
        self.lang = lang
        self.directory = os.path.join(os.path.dirname(__file__), "locale", lang)
        for fname in os.listdir(self.directory):
            name = os.path.splitext(fname)[0]
            samples = load_template_file(os.path.join(self.directory, fname))
            setattr(self, name, Keyword(name=name, samples=samples))
            if DEBUG:
                print(f"   - DEBUG: Found builtin keyword: {name} / {samples}")
