import threading
from dataclasses import dataclass
from typing import Callable, List, Union, Tuple, Optional

from text_engine.dialog import DialogRenderer
from text_engine.intents import Keyword, KeywordIntent, IntentEngine

# Typing aliases
GetUserInputHandler = Optional[Callable[['IFGameEngine', str], str]]  # args: game, input_prompt
PrintOutputHandler = Optional[Callable[['IFGameEngine', str], None]]  # args: game, output
WinConditionCheck = Callable[['IFGameEngine'], bool]
GameCallbackHandler = Optional[Callable[['IFGameEngine'], None]]
GameInputCallbackHandler = Optional[Callable[['IFGameEngine', str], None]]  # args: game, input
GameOutputCallbackHandler = Optional[Callable[['IFGameEngine', str, str], None]]  # args: game, input, output


@dataclass
class GameHandlers:
    """
    Callbacks for various game events.

    Attributes:
        is_win: Callable that determines if the game is won.
        is_loss: Callable that determines if the game is lost.
        on_start: Called before the first game turn.
        on_win: Called when the game is won.
        on_lose: Called when the game is lost.
        on_end: Called after the game ends (win or lose).
        before_interaction: Called before user interaction.
        after_interaction: Called after user interaction.
        before_turn: Called before each game turn.
        end_turn: Called after each game turn, before advancing.
        after_turn: Called after each game turn, after advancing.
        on_input: Called when the game wants to get user input
        on_print: Called when the game wants to output text
    """
    is_win: WinConditionCheck
    is_loss: WinConditionCheck
    on_start: GameCallbackHandler = None
    on_win: GameCallbackHandler = None
    on_lose: GameCallbackHandler = None
    on_end: GameCallbackHandler = None
    before_interaction: GameInputCallbackHandler = None
    after_interaction: GameOutputCallbackHandler = None
    before_turn: GameCallbackHandler = None
    end_turn: GameCallbackHandler = None
    after_turn: GameCallbackHandler = None
    on_input: GetUserInputHandler = lambda g, u: input(u)  # allow games to get user input their own way
    on_print: PrintOutputHandler = lambda g, u: print(u)  # allow games to handle print their own way


@dataclass
class GameIntents:
    """
    Intent parser and handler for the game.

    Attributes:
        intents: List of KeywordIntent objects.
        parser: IntentEngine used for parsing intents.
    """
    intents: List[KeywordIntent]
    parser: IntentEngine = IntentEngine()

    def __post_init__(self):
        for intent in self.intents:
            self.parser.register_intent(intent)

    def predict(self, utterance: str) -> Tuple[Optional[KeywordIntent], float]:
        """
        Predict the intent for a given utterance.

        Args:
            utterance: The user's input.

        Returns:
            A tuple containing the matched intent (if any) and its confidence score.
        """
        intents = self.parser.calc_intents(utterance)
        if intents:
            return intents[0]
        return None, 0.0


@dataclass
class GameScene:
    """
    Represents a scene in the game.

    Attributes:
        description: Description of the scene.
        game_objects: List of objects within the scene.
        active_object: Index of the currently active game object.
        intents: GameIntents for handling scene-specific interactions.
    """
    description: str
    game_objects: Optional[List['GameObject']] = None
    active_object: int = -1  # idx from game_objects
    intents: Optional[GameIntents] = None

    def __post_init__(self):
        self.game_objects = self.game_objects or []

    def refocus(self):
        """Refocus the scene, deactivating any active object."""
        self.active_object: int = -1

    def interact(self, game: 'IFGameEngine', utterance: str) -> str:
        """
        Process user interaction within the scene.

        Args:
            game: The game engine instance.
            utterance: The user's input.

        Returns:
            A response string based on the interaction.
        """
        if self.intents:
            intent, score = self.intents.predict(utterance)
            if score > 0.5:
                # change scenes here if needed via game.activate/add/remove_scene
                return intent.handler(game, utterance)

        if not self.game_objects or self.active_object == -1:
            return self.description
        # change self.active_object here as needed
        return self.game_objects[self.active_object].interact(game=game,
                                                              utterance=utterance)


@dataclass
class GameObject:
    """
    Represents an object within a game scene.

    Attributes:
        name: Keyword representing the object's name.
        intent_handlers: Intent parser and handler specific to the object.
        default_dialog: Default response when no intent is matched.
    """
    name: Keyword
    intent_handlers: GameIntents
    default_dialog: str

    def bye(self, game: 'IFGameEngine'):
        """Refocus the scene, deactivating this object."""
        game.active_scene.refocus()

    def interact(self, game: 'IFGameEngine', utterance: str) -> str:
        """
        Process user interaction with the object.

        Args:
            game: The game engine instance.
            utterance: The user's input.

        Returns:
            A response string based on the interaction.
        """
        intent, score = self.intent_handlers.predict(utterance)
        # change game.active_scene.active_object here as needed
        if score < 0.5:
            return self.default_dialog
        return intent.handler(game, utterance)


class IFGameEngine(threading.Thread):
    """
    Interactive Fiction Game Engine.

    Attributes:
        scenes: List of game scenes.
        handlers: Event callbacks.
        dialog_renderer: Renderer for dialog texts.
    """

    def __init__(self,
                 scenes: List['GameScene'],
                 handlers: GameHandlers,
                 dialog_renderer: Optional[DialogRenderer] = None):
        super().__init__()
        self.current_turn: int = 1
        self.scenes = scenes
        self.handlers = handlers
        self.running = threading.Event()
        self._active_scene = 0
        self.dialog_renderer = dialog_renderer
        assert len(self.scenes) > 0

    def print(self, text: str):
        """Print a message to the console."""
        self.handlers.on_print(self, text)

    def get_dialog(self, name: str) -> str:
        """
        Retrieve a dialog by name.

        Args:
            name: The name of the dialog.

        Returns:
            The dialog text.
        """
        return self.dialog_renderer.get_dialog(name)

    def speak_dialog(self, name: str):
        """Retrieve and print a dialog by name."""
        self.print(self.get_dialog(name))

    @property
    def active_scene(self) -> 'GameScene':
        """Return the currently active scene."""
        return self.scenes[self._active_scene]

    def activate_scene(self, scene: Union[int, 'GameScene']):
        """
        Activate a specific scene.

        Args:
            scene: The scene to activate (by index or instance).
        """
        if isinstance(scene, int):
            self._active_scene = scene
        else:
            self._active_scene = self.scenes.index(scene)
        self.print(self.active_scene.description)

    def add_scene(self, scene: 'GameScene'):
        """Add a new scene to the game."""
        if scene not in self.scenes:
            self.scenes.append(scene)

    def remove_scene(self, scene: Union[int, 'GameScene']):
        """
        Remove a scene from the game.

        Args:
            scene: The scene to remove (by index or instance).
        """
        if isinstance(scene, int):
            scene = self.scenes[scene]
        self.scenes.remove(scene)

    def run(self):
        """Run the game loop."""
        self.running.set()
        if self.handlers.on_start:
            self.handlers.on_start(self)
        self.print(self.active_scene.description)
        while self.running.is_set():
            if self.handlers.before_turn:
                self.handlers.before_turn(self)
            utt = input("> ")

            if self.handlers.before_interaction:
                self.handlers.before_interaction(self, utt)

            ans = self.active_scene.interact(self, utt)

            if self.handlers.after_interaction:
                self.handlers.after_interaction(self, utt, ans)

            if ans:
                self.print(ans)

            if self.handlers.is_win(self):
                if self.handlers.on_win:
                    self.handlers.on_win(self)
                break
            if self.handlers.is_loss(self):
                if self.handlers.on_lose:
                    self.handlers.on_lose(self)
                break
            if self.handlers.end_turn:
                self.handlers.end_turn(self)
            self.advance()
            if self.handlers.after_turn:
                self.handlers.after_turn(self)

        self.running.clear()
        if self.handlers.on_end:
            self.handlers.on_end(self)

    def advance(self):
        """advance to next turn"""
        self.current_turn += 1
