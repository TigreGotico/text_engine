import threading
from dataclasses import dataclass
from typing import Callable, List, Union, Tuple, Optional

from text_engine.intents import Keyword, KeywordIntent, IntentEngine
from text_engine.dialog import DialogRenderer


@dataclass
class Conditions:
    is_win: Callable[['IFGameEngine'], bool]
    is_loss: Callable[['IFGameEngine'], bool]


@dataclass
class Callbacks:
    on_start: Optional[Callable[['IFGameEngine'], None]] = None
    on_end: Optional[Callable[['IFGameEngine'], None]] = None
    on_win: Optional[Callable[['IFGameEngine'], None]] = None
    on_lose: Optional[Callable[['IFGameEngine'], None]] = None
    on_utterance: Optional[Callable[['IFGameEngine', str], None]] = None


@dataclass
class GameIntents:
    intents: List[KeywordIntent]
    parser: IntentEngine = IntentEngine()

    def __post_init__(self):
        for intent in self.intents:
            self.parser.register_intent(intent)

    def predict(self, utterance: str) -> Tuple[Optional[KeywordIntent], float]:
        intents = self.parser.calc_intents(utterance)
        if intents:
            return intents[0]
        return None, 0.0


@dataclass
class GameScene:
    description: str
    game_objects: Optional[List['GameObject']] = None
    active_object: int = -1  # idx from game_objects
    intents: Optional[GameIntents] = None

    def __post_init__(self):
        self.game_objects = self.game_objects or []

    def refocus(self):
        self.active_object: int = -1

    def interact(self, game: 'IFGameEngine', utterance: str):
        if self.intents:
            intent, score = self.intents.predict(utterance)
            if score > 0.5:
                # change scenes here if needed via game.activate/add/remove_scene
                return intent.handler(game, utterance)

        if not len(self.game_objects) or self.active_object == -1:
            return self.description
        # change self.active_object here as needed
        return self.game_objects[self.active_object].interact(game=game,
                                                              utterance=utterance)


@dataclass
class GameObject:
    name: Keyword
    intent_handlers: GameIntents
    default_dialog: str

    def bye(self, game: 'IFGameEngine'):
        # refocus scene instead of object
        game.active_scene.refocus()

    def interact(self, game: 'IFGameEngine', utterance: str) -> str:
        intent, score = self.intent_handlers.predict(utterance)
        # change game.active_scene.active_object here as needed
        if score < 0.5:
            return self.default_dialog
        return intent.handler(game, utterance)


class IFGameEngine(threading.Thread):
    def __init__(self,
                 scenes: List['GameScene'],
                 conditions: Conditions,
                 callbacks: Callbacks = Callbacks(),
                 dialog_renderer: Optional[DialogRenderer] = None):
        super().__init__()
        self.current_turn: int = 1
        self.scenes = scenes
        self.callbacks = callbacks
        self.checks = conditions
        self.running = threading.Event()
        self._active_scene = 0
        self.dialog_renderer = dialog_renderer
        assert len(self.scenes) > 0

    def print(self, text: str):
        # TODO - allow defining text color and such ?
        print(text)

    def get_dialog(self, name: str) -> str:
        return self.dialog_renderer.get_dialog(name)

    def speak_dialog(self, name: str):
        self.print(self.get_dialog(name))

    @property
    def active_scene(self) -> 'GameScene':
        return self.scenes[self._active_scene]

    def activate_scene(self, scene: Union[int, 'GameScene']):
        if isinstance(scene, int):
            self._active_scene = scene
        else:
            self._active_scene = self.scenes.index(scene)
        self.print(self.active_scene.description)

    def add_scene(self, scene: 'GameScene'):
        if scene not in self.scenes:
            self.scenes.append(scene)

    def remove_scene(self, scene: Union[int, 'GameScene']):
        if isinstance(scene, int):
            scene = self.scenes[scene]
        self.scenes.remove(scene)

    def run(self):
        self.running.set()
        if self.callbacks.on_start:
            self.callbacks.on_start(self)
        self.print(self.active_scene.description)
        while self.running.is_set():
            utt = input("> ")
            if self.callbacks.on_utterance:
                self.callbacks.on_utterance(self, utt)

            ans = self.active_scene.interact(self, utt)
            if ans:
                self.print(ans)

            if self.checks.is_win(self):
                if self.callbacks.on_win:
                    self.callbacks.on_win(self)
                break
            if self.checks.is_loss(self):
                if self.callbacks.on_lose:
                    self.callbacks.on_lose(self)
                break
            self.advance()

        self.running.clear()
        if self.callbacks.on_end:
            self.callbacks.on_end(self)

    def advance(self):
        self.current_turn += 1
