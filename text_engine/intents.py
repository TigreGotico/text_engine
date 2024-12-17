import os.path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Callable

from json_database import JsonStorage

try:
    from quebra_frases import word_tokenize
except ImportError:
    def word_tokenize(text: str, *args, **kwargs) -> List[str]:
        return text.split()


DEBUG = False  # just a helper during development

# for typing
IntentHandler = Callable[['IFGameEngine', str], str]


@dataclass
class Keyword:
    name: str
    samples: Optional[List[str]] = None

    def __post_init__(self):
        self.samples = self.samples or [self.name]

    @property
    def file_path(self) -> str:
        return os.path.join("keywords", f"{self.name}.voc")

    def save(self, directory: str):
        path = os.path.join(directory, self.file_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("\n".join(self.samples))
        if DEBUG:
            print(f"   - DEBUG: saved keyword to file: {self.name} / {path}")

    @classmethod
    def from_file(cls, path: str) -> 'Keyword':
        name = path.split("/")[-1].split(".voc")[0]
        with open(path) as f:
            samples = [l for l in f.read().split("\n") if l]
        if DEBUG:
            print(f"   - DEBUG: loaded keyword from file: {name} / {samples}")
        return Keyword(name=name, samples=samples)

    def reload(self, directory: str):
        path = os.path.join(directory, self.file_path)
        if os.path.isfile(path):
            self.name = path.split("/")[-1].split(".voc")[0]
            with open(path) as f:
                self.samples = [l for l in f.read().split("\n") if l]

    def match(self, utterance: str) -> bool:
        return any([s.lower() in utterance.lower()
                    for s in self.samples])


@dataclass
class KeywordIntent:
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
        return os.path.join("intents", f"{self.name}.json")

    def save(self, directory: str):
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
        db = JsonStorage(path)
        required = [Keyword(k) for k in db["required"]]
        excludes = [Keyword(k) for k in db["excludes"]]
        optional = [Keyword(k) for k in db["optional"]]
        intent = KeywordIntent(name=db["name"], required=required,
                               optional=optional, excludes=excludes)
        if DEBUG:
            print(f"   - DEBUG: loaded intent from file: {intent.name} / {db}")
        directory = os.path.dirname(os.path.dirname(path))
        for k in intent.required + intent.excludes + intent.optional:
            k.reload(directory=directory)
        return intent

    def reload(self, directory: str):
        path = os.path.join(directory, self.file_path)
        if os.path.isfile(path):
            db = JsonStorage(path)
            self.name = db["name"]
            self.required = [Keyword(k) for k in db["required"]]
            self.excludes = [Keyword(k) for k in db["excludes"]]
            self.optional = [Keyword(k) for k in db["optional"]]
            # reload keywords from file to also load "samples"
            for k in self.required + self.excludes + self.optional:
                k.reload(directory=directory)

    def score(self, utterance: str) -> float:
        # Check for excluded keywords first
        if any(ent.match(utterance) for ent in self.excludes):
            return 0.0

        # Match required and optional keywords
        matched_required = sum(1 for ent in self.required if ent.match(utterance))
        matched_optional = sum(1 for ent in self.optional if ent.match(utterance))
        total_required = len(self.required)
        total_optional = len(self.optional)

        # If not all required keywords are matched, return 0.0
        if matched_required < total_required:
            return 0.0

        # Scoring based on required and optional matches
        if total_required > 0 and total_optional > 0:
            # Blend the contribution of required and optional matches
            required_score = matched_required / total_required
            optional_score = matched_optional / total_optional
            overall_score = 0.8 + (0.2 * optional_score)  # Boost if optional matches
        else:
            # Fallback when there are no optional keywords
            overall_score = 0.8

        # Ensure a minimum score of 0.5 if some required keywords match
        return max(overall_score, 0.5)


class IntentEngine:
    """individual games may subclass this"""

    def __init__(self, intent_cache: Optional[str] = None):
        self.intents: Dict[str, KeywordIntent] = {}
        self.cache = intent_cache
        if self.cache:
            intents_path = os.path.join(self.cache, "intents")
            if os.path.isdir(intents_path):
                for fname in os.listdir(intents_path):
                    if not fname.endswith(".json"):
                        continue
                    intent = KeywordIntent.from_file(os.path.join(intents_path, fname))
                    self.intents[intent.name] = intent

    def calc_intents(self, utterance: str) -> List[Tuple[KeywordIntent, float]]:
        # calc intent + conf
        candidates = []
        for name, intent in self.intents.items():
            score = intent.score(utterance)
            if score >= 0.5:
                candidates.append(intent)  # match!
                if DEBUG:
                    print(f"    - DEBUG: intent: {name} / {score}")

        return sorted([(i, i.score(utterance)) for i in candidates],
                      key=lambda k: k[1], reverse=True)

    def register_intent(self, intent: KeywordIntent):
        self.intents[intent.name] = intent
        if DEBUG:
            print(f"    - DEBUG: registering intent: {intent.name}")
        #if self.cache:
        #    intent.save(self.cache)

    def deregister_intent(self, name: str):
        if name in self.intents:
            intent = self.intents.pop(name)
            if self.cache:
                path = os.path.join(self.cache, intent.file_path)
                if os.path.isfile(path):
                    os.remove(path)


class BuiltinKeywords:
    def __init__(self, lang: str):
        self.lang = lang
        self.directory = os.path.join(os.path.dirname(__file__), "locale", lang)
        for fname in os.listdir(self.directory):
            name = fname.split(".voc")[0]
            with open(os.path.join(self.directory, fname)) as f:
                samples = [l for l in f.read().split("\n") if l and not l.startswith("# ")]
            kw = Keyword(name=name, samples=samples)
            self.__setattr__(name, kw)
            if DEBUG:
                print(f"   - DEBUG: Found builtin keyword: {name} / {samples}")

