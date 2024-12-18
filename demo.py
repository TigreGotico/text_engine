"""simple single scene game with no game objects"""
from text_engine import (GameHandlers, GameScene, Keyword, KeywordIntent, GameIntents, IFGameEngine)


class TheRoom(GameScene):
    def __init__(self):
        self.inventory = []

        # Define the scene entities
        self.key = Keyword(name="key")
        self.door = Keyword(name="door")
        self.window = Keyword(name="window")
        self.table = Keyword(name="table")

        # Define the intents for interacting with the scene
        look_intent = KeywordIntent(
            name="look",
            required=[Keyword(name="look")],
            optional=[self.key, self.door, self.window, self.table],
            handler=self.on_look
        )
        open_door_intent = KeywordIntent(
            name="open_door",
            required=[Keyword(name="open"), self.door],
            handler=self.on_open_door
        )
        open_window_intent = KeywordIntent(
            name="open_window",
            required=[Keyword(name="open"), self.window],
            handler=self.on_open_window
        )
        take_key_intent = KeywordIntent(
            name="take_key",
            required=[Keyword(name="take"), self.key],
            handler=self.on_take_key
        )
        use_key_intent = KeywordIntent(
            name="use_key",
            required=[Keyword(name="use"), self.key, self.door],
            handler=self.on_use_key
        )
        # this scene has no objects, if it did we should always have a
        # "back" intent in each object to refocus the scene
        # game.active_scene.active_object = -1
        super().__init__("you are in a dimly lit room",
                         intents=GameIntents([take_key_intent,
                                              look_intent,
                                              use_key_intent,
                                              open_door_intent]))

    # scene logic/intents
    def on_take_key(self, game: IFGameEngine, utterance: str):
        if "key" not in self.inventory:
            self.inventory.append("key")
            return "You pick up the small metal key."
        else:
            return "You already have the key."

    def on_open_door(self, game: IFGameEngine, utterance: str):
        if "key" in self.inventory:
            return "The door is locked. Maybe you need to use the key?"
        else:
            return "The door is locked. You need to find a way to open it."

    def on_open_window(self, game: IFGameEngine, utterance: str):
        return "The window is stuck shut. You won't get out this way."

    def on_use_key(self, game: IFGameEngine, utterance: str):
        if "key" in self.inventory:
            game.running.clear()  # End the game
            return "You unlock the door with the key."
        else:
            return "You don't have the key."

    def on_look(self, game: IFGameEngine, utterance: str):
        if self.table.match(utterance):
            if "key" in self.inventory:
                return "You see a dusty table"
            return "You see a small key on the table."
        elif self.key.match(utterance):
            if "key" in self.inventory:
                return "The key is small and rusty"
            return "You see a small key on the table."
        elif self.door.match(utterance):
            return "The door is locked. It looks sturdy."
        elif self.window.match(utterance):
            return "The window is stuck shut. You won't get out this way."
        else:
            return "The room is small and empty, except for a table and a door."


class EscapeRoom(IFGameEngine):
    def __init__(self):
        super().__init__(
            scenes=[TheRoom()],
            handlers=GameHandlers(on_end=self.on_end,
                                  on_start=self.on_start,
                                  on_win=lambda k: print("Congratulations! You escaped the room."),
                                  on_lose=lambda k: print("You ran out of oxygen and died!"),
                                  is_loss=self.is_loss, is_win=self.is_win))

    def on_start(self, game: IFGameEngine):
        game.print("You wake up in a locked room. There is a table with something on it.")
        game.print("Type commands to look around, pick up items, and interact with objects.")
        game.print("For example: 'look at key', 'take key', 'open door', or 'use key on door'.")

    def on_end(self, game: IFGameEngine):
        game.print("Game Over. Thanks for playing!")

    def is_win(self, game: IFGameEngine) -> bool:
        return not game.running.is_set()  # If game stops running, it's a win

    def is_loss(self, game: IFGameEngine) -> bool:
        return game.current_turn > 3


if __name__ == "__main__":
    EscapeRoom().run()
