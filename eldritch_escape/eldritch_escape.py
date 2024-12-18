"""based on demo.py but with actual gameplay

uses builtin common keywords (mostly verbs and common objects)

dialogs/keywords come from files, locale folder similar to OVOS.
this allows easy translation while also abstracting the game engine away
completely new games can be made by just changing resource files
"""
import os.path
import random

from text_engine import GameHandlers, GameScene, Keyword, KeywordIntent, GameIntents, IFGameEngine, IntentEngine
from text_engine.dialog import DialogRenderer
from text_engine.intents import BuiltinKeywords
from text_engine.engine import GetUserInputHandler, PrintOutputHandler


class TheCursedRoom(GameScene):
    def __init__(self, locale_folder: str, lang: str, default_response: str):
        self.got_key = False
        self.n_listens = 0
        self.inventory = ["cassette"]
        self.destroyed = []
        self.max_sanity = 10  # Sanity level (difficulty setting can change this)
        self.sanity = self.max_sanity

        # Define the scene entities/keywords
        # some Keyword definitions are bundled with the engine
        #  mainly for verbs: look, grab, drop, move, touch, smell, read, watch, use, help...
        self.builtin = BuiltinKeywords(lang)

        # load lang keywords from resource files
        kw_path = os.path.join(locale_folder, lang, "keywords")
        room = Keyword.from_file(os.path.join(kw_path, "room.voc"))
        self.altar = Keyword.from_file(os.path.join(kw_path, "altar.voc"))
        self.symbols = Keyword.from_file(os.path.join(kw_path, "symbols.voc"))
        self.floor = Keyword.from_file(os.path.join(kw_path, "floorboards.voc"))
        self.slime = Keyword.from_file(os.path.join(kw_path, "slime.voc"))
        self.cassette = Keyword.from_file(os.path.join(kw_path, "cassette.voc"))

        # Intents for interacting with the scene
        # TODO - repair_intent, increase player frustration if they try to put back mirror/painting/book/cassette
        look_intent = KeywordIntent(
            name="look",
            required=[self.builtin.look],
            optional=[room, self.altar, self.floor, self.slime, self.cassette,
                      self.builtin.key, self.builtin.door, self.builtin.window,
                      self.builtin.mirror, self.builtin.book, self.builtin.painting],
            handler=self.on_look
        )
        listen_intent = KeywordIntent(
            name="listen",
            required=[self.builtin.listen],
            optional=[room, self.floor, self.slime, self.builtin.door, self.builtin.window,
                      self.builtin.wall, self.cassette],
            handler=self.on_listen
        )
        destroy_intent = KeywordIntent(
            name="destroy",
            required=[self.builtin.destroy],
            optional=[self.floor, self.cassette, self.altar,
                      self.builtin.door, self.builtin.book, self.builtin.painting,
                      self.builtin.window, self.builtin.wall, self.builtin.mirror],
            handler=self.on_destroy
        )
        take_intent = KeywordIntent(
            name="take",
            required=[self.builtin.grab],
            optional=[self.builtin.mirror, self.builtin.key, self.builtin.book,
                      self.builtin.painting, self.cassette],
            handler=self.on_take
        )
        drop_intent = KeywordIntent(
            name="drop",
            required=[self.builtin.drop],
            optional=[self.cassette, self.builtin.key],
            handler=self.on_drop
        )
        use_intent = KeywordIntent(
            name="use",
            required=[self.builtin.use],
            optional=[self.cassette, self.builtin.key],
            handler=self.on_use
        )
        open_intent = KeywordIntent(
            name="open",
            required=[self.builtin.open],
            optional=[self.builtin.window, self.builtin.door, self.builtin.book],
            handler=self.on_open
        )
        read_intent = KeywordIntent(
            name="read",
            required=[self.builtin.read],
            optional=[self.builtin.book, self.builtin.wall, self.altar, self.symbols],
            handler=self.on_read
        )
        move_intent = KeywordIntent(
            name="move",
            required=[self.builtin.move],
            optional=[self.floor, self.altar, self.cassette, self.builtin.book,
                      self.builtin.key, self.builtin.mirror, self.builtin.painting],
            handler=self.on_move
        )
        smell_intent = KeywordIntent(
            name="smell",
            required=[self.builtin.smell],
            optional=[self.slime, self.floor, self.altar, room, self.cassette,
                      self.builtin.wall, self.builtin.door, self.builtin.window, self.builtin.book,
                      self.builtin.key, self.builtin.mirror, self.builtin.painting],
            handler=self.on_smell
        )
        touch_intent = KeywordIntent(
            name="touch",
            required=[self.builtin.touch],
            optional=[self.slime, self.floor, self.altar, self.cassette,
                      self.builtin.wall, self.builtin.door, self.builtin.window, self.builtin.book,
                      self.builtin.key, self.builtin.mirror, self.builtin.painting],
            handler=self.on_touch
        )
        help_intent = KeywordIntent(
            name="help",
            required=[self.builtin.help],
            handler=self.on_help
        )
        super().__init__(default_response,
                         intents=GameIntents(parser=IntentEngine(intent_cache=f"{locale_folder}/{lang}"),
                                             intents=[
                                                 look_intent, help_intent, read_intent, open_intent, touch_intent,
                                                 smell_intent, take_intent, move_intent, listen_intent, drop_intent,
                                                 use_intent, destroy_intent]))

    # game mechanics
    def decrease_sanity(self, game: IFGameEngine, decrement: int):
        self.sanity -= decrement
        if self.sanity <= 0:
            return f"{game.get_dialog('no_more_sanity')}\n{game.dialog_renderer.get_text('sanity')}: 0/{self.max_sanity}."
        stages = [
            game.get_dialog("sanity_1"),
            game.get_dialog("sanity_2"),
            game.get_dialog("sanity_3"),
            game.get_dialog("sanity_4"),
            game.get_dialog("sanity_5")
        ]
        level = max(0, min(self.sanity // 2, len(stages) - 1))
        return f"{stages[level]}\n{game.dialog_renderer.get_text('sanity')}: {self.sanity}/{self.max_sanity}."

    def increase_sanity(self, game: IFGameEngine, increment: int):
        self.sanity += increment
        return f"{game.dialog_renderer.get_text('sanity')}: {self.sanity}/{self.max_sanity}."

    def escape_via_floorboards(self, game: IFGameEngine, utterance: str):
        # Sanity threshold to allow moving the floorboards
        sanity_threshold = self.max_sanity / 2  # half of sanity needs to be lost before moving floorboards is allowed
        if self.sanity > sanity_threshold:
            # If sanity is not low enough, the game refuses the action and gives an excuse
            return game.get_dialog("move_floor_refuse")
        else:
            # If sanity is low enough, allow the action to proceed and end the game
            # This is how you win the game
            game.running.clear()
            return game.get_dialog("move_floor")

    def on_error(self, game: IFGameEngine, utterance: str):
        """catch all for invalid actions"""
        return game.get_dialog("error")

    def on_help(self, game: IFGameEngine, utterance: str):
        """help dialog"""
        return game.get_dialog("help_commands") + "\n" + game.get_dialog("valid_actions")

    def on_use(self, game: IFGameEngine, utterance: str):
        if (self.builtin.key.match(utterance) or
                self.builtin.door.match(utterance) or
                self.builtin.window.match(utterance)):
            return self.on_open(game, utterance)
        elif self.cassette.match(utterance):
            return self.on_listen(game, utterance)
        else:
            return self.on_error(game, utterance)

    def on_destroy(self, game: IFGameEngine, utterance: str):
        if self.floor.match(utterance):
            return self.escape_via_floorboards(game, utterance)
        elif self.slime.match(utterance):
            return game.get_dialog("destroy_slime_fail") + f"\n{self.decrease_sanity(game, 1)}"
        elif self.altar.match(utterance):
            return game.get_dialog("destroy_altar_fail")
        elif self.builtin.key.match(utterance):
            return game.get_dialog("destroy_key_fail")
        elif self.builtin.door.match(utterance):
            return game.get_dialog("destroy_door_fail")
        elif self.builtin.wall.match(utterance):
            return game.get_dialog("destroy_wall_fail")
        elif self.builtin.window.match(utterance):
            return game.get_dialog("destroy_window_fail")
        elif self.builtin.book.match(utterance):
            if "book" in self.destroyed:
                return game.get_dialog("destroy_book_aftermath")
            else:
                self.destroyed.append("book")
                return game.get_dialog("destroy_book") + "\n" + self.increase_sanity(game, 1)
        elif self.builtin.mirror.match(utterance):
            if "mirror" in self.destroyed:
                return game.get_dialog("destroy_mirror_aftermath")
            else:
                self.destroyed.append("mirror")
                return game.get_dialog("destroy_mirror")
        elif self.builtin.painting.match(utterance):
            if "painting" in self.destroyed:
                return game.get_dialog("destroy_painting_aftermath") + "\n" + self.increase_sanity(game, 1)
            else:
                self.destroyed.append("painting")
                return game.get_dialog("destroy_painting")
        elif self.cassette.match(utterance):
            if "cassette" in self.destroyed:
                return game.get_dialog("destroy_cassette_aftermath")
            else:
                self.destroyed.append("cassette")
                if "cassette" in self.inventory:
                    self.inventory.remove("cassette")
                return game.get_dialog("destroy_cassette")
        else:
            return self.on_error(game, utterance)

    def on_take(self, game: IFGameEngine, utterance: str):
        if self.builtin.key.match(utterance):
            self.got_key = True
            if "key" not in self.inventory:
                self.inventory.append("key")
                return game.get_dialog("take_key") + f"\n{self.decrease_sanity(game, 1)}"
            else:
                return game.get_dialog("take_key_already")
        elif self.cassette.match(utterance):
            if "cassette" in self.destroyed:
                return game.get_dialog("destroy_cassette_aftermath")
            elif "cassette" not in self.inventory:
                self.inventory.append("cassette")
                return game.get_dialog("take_cassette")
            else:
                return game.get_dialog("take_cassette_already")
        elif self.builtin.painting.match(utterance):
            if "painting" in self.destroyed:
                return game.get_dialog("destroy_painting_aftermath")
            return game.get_dialog("move_painting")
        elif self.builtin.mirror.match(utterance):
            if "mirror" in self.destroyed:
                return game.get_dialog("destroy_mirror_aftermath")
            return game.get_dialog("move_mirror")
        elif self.builtin.book.match(utterance):
            if "book" in self.destroyed:
                return game.get_dialog("destroy_book_aftermath")
            return game.get_dialog("move_book")
        else:
            return self.on_error(game, utterance)

    def on_drop(self, game: IFGameEngine, utterance: str):
        if self.cassette.match(utterance):
            if "cassette" in self.destroyed:
                return game.get_dialog("destroy_cassette_aftermath")
            elif "cassette" in self.inventory:
                return game.get_dialog("drop_cassette")
            else:
                return game.get_dialog("drop_cassette_no_cassette")
        elif not self.builtin.key.match(utterance):
            return self.on_error(game, utterance)

        if "key" in self.inventory:
            self.inventory.remove("key")
            response = f"{game.get_dialog('drop_key')}\n{game.get_dialog('drop_key_sanity')}"
            if self.sanity < self.max_sanity / 2:
                response += f"\n{game.get_dialog('drop_key_low_sanity')}"
            return response + self.increase_sanity(game, 1)
        else:
            if self.got_key:
                # Case where the player previously had the key:
                return game.get_dialog("drop_key_no_key")
            else:
                # Case where the player never had the key:
                return f"{game.get_dialog('drop_key_never_had_key')} {self.decrease_sanity(game, 1)}"

    def on_open(self, game: IFGameEngine, utterance: str):
        if self.builtin.door.match(utterance) or self.builtin.key.match(utterance):
            if "key" in self.inventory:
                # The key is ultimately useless, no win condition
                return game.get_dialog("open_door_with_key") + f"\n{self.decrease_sanity(game, 1)}"
            else:
                return game.get_dialog("open_door_no_key")
        elif self.builtin.window.match(utterance):
            return game.get_dialog("open_window")
        elif self.builtin.book.match(utterance):
            if "book" in self.destroyed:
                return game.get_dialog("destroy_book_aftermath")
            return game.get_dialog("read_book")
        else:
            return self.on_error(game, utterance)

    def on_look(self, game: IFGameEngine, utterance: str):
        if self.altar.match(utterance):
            response = game.get_dialog('look_altar')
            if "key" in self.inventory:
                return response
            return response + "\n" + game.get_dialog("key_in_altar")
        elif self.symbols.match(utterance):
            return f"{game.get_dialog('look_symbols')}\n{self.decrease_sanity(game, 2)}"
        elif self.cassette.match(utterance):
            if "cassette" in self.destroyed:
                return game.get_dialog("destroy_cassette_aftermath")
            return game.get_dialog('look_cassette')
        elif self.builtin.key.match(utterance):
            return game.get_dialog('look_key')
        elif self.builtin.door.match(utterance):
            return game.get_dialog('look_door')
        elif self.builtin.window.match(utterance):
            return game.get_dialog('look_window')
        elif self.builtin.book.match(utterance):
            if "book" in self.destroyed:
                return game.get_dialog("destroy_book_aftermath")
            return game.get_dialog('look_book')
        elif self.slime.match(utterance):
            return game.get_dialog('look_slime')
        elif self.builtin.mirror.match(utterance):
            if "mirror" in self.destroyed:
                return game.get_dialog("destroy_mirror_aftermath")
            return f"{game.get_dialog('peer_mirror')}\n{game.get_dialog('look_mirror')}\n{self.decrease_sanity(game, 1)}"
        elif self.builtin.painting.match(utterance):
            if "painting" in self.destroyed:
                return game.get_dialog("destroy_painting_aftermath")
            return game.get_dialog('look_painting') + f"\n{self.decrease_sanity(game, 1)}"
        elif self.floor.match(utterance):
            return game.get_dialog('look_floor') + f"\n{self.decrease_sanity(game, 1)}"
        else:
            # NOTE: the painting might be mentioned or not
            room = game.get_dialog("look_room")

            # dialog mentioning things to be looked at: slime, book, table, key, door, window, painting
            window_message = game.get_dialog("window_description")
            slime_message = game.get_dialog("slime_description")
            altar_message = game.get_dialog("altar_description")
            door_message = game.get_dialog("door_description")
            book_message = game.get_dialog("book_description")
            painting_message = game.get_dialog("painting_description")
            mirror_message = game.get_dialog("mirror_description")
            cassette_message = game.get_dialog("cassette_description")

            items = [window_message, slime_message, altar_message, door_message]

            if "book" not in self.destroyed:
                items.append(book_message)
            if "mirror" not in self.destroyed:
                items.append(mirror_message)
            if "cassette" not in self.destroyed:
                items.append(cassette_message)
            if "painting" not in self.destroyed and random.choice([True, False, False]):
                items.append(painting_message)
            random.shuffle(items)

            if game.current_turn > 5:
                # after N turns start mentioning the floor to give a clue how to escape
                if self.sanity < self.max_sanity / 4 or game.current_turn >= 15:
                    floor_message = game.get_dialog("floor_description_low_sanity")
                else:
                    floor_message = game.get_dialog("floor_description")
                items.append(floor_message)

            items_message = "\n".join(items)

            return f"{room}.\n{items_message}"

    def on_move(self, game: IFGameEngine, utterance: str):
        if self.builtin.painting.match(utterance):
            if "painting" in self.destroyed:
                return game.get_dialog("destroy_painting_aftermath")
            return game.get_dialog("move_painting")
        elif self.altar.match(utterance):
            return game.get_dialog("move_altar")
        elif self.cassette.match(utterance):
            if "cassette" in self.destroyed:
                return game.get_dialog("destroy_cassette_aftermath")
            return game.get_dialog("move_cassette")
        elif self.builtin.mirror.match(utterance):
            if "mirror" in self.destroyed:
                return game.get_dialog("destroy_mirror_aftermath")
            return game.get_dialog("move_mirror")
        elif self.builtin.key.match(utterance):
            return game.get_dialog("move_key")
        elif self.builtin.book.match(utterance):
            if "book" in self.destroyed:
                return game.get_dialog("destroy_book_aftermath")
            return game.get_dialog("move_book")
        elif self.floor.match(utterance):
            return self.escape_via_floorboards(game, utterance)
        else:
            return self.on_error(game, utterance)

    def on_touch(self, game: IFGameEngine, utterance: str):
        if self.builtin.painting.match(utterance):
            if "painting" in self.destroyed:
                return game.get_dialog("destroy_painting_aftermath")
            return game.get_dialog("touch_painting")
        elif self.builtin.mirror.match(utterance):
            if "mirror" in self.destroyed:
                return game.get_dialog("destroy_mirror_aftermath")
            return game.get_dialog("touch_mirror")
        elif self.cassette.match(utterance):
            if "cassette" in self.destroyed:
                return game.get_dialog("destroy_cassette_aftermath")
            return game.get_dialog("touch_cassette")
        elif self.builtin.window.match(utterance):
            return game.get_dialog("touch_window")
        elif self.builtin.door.match(utterance):
            return game.get_dialog("touch_door")
        elif self.builtin.wall.match(utterance):
            return game.get_dialog("touch_wall")
        elif self.floor.match(utterance):
            return game.get_dialog("touch_floor")
        elif self.builtin.key.match(utterance):
            return game.get_dialog("touch_key")
        elif self.builtin.book.match(utterance):
            if "book" in self.destroyed:
                return game.get_dialog("destroy_book_aftermath")
            return game.get_dialog("touch_book")
        elif self.altar.match(utterance):
            return game.get_dialog("touch_altar")
        elif self.slime.match(utterance):
            response = game.get_dialog("touch_slime")
            sanity_impact = random.choice([1, 2, 3])
            return f"{response}\n{self.decrease_sanity(game, sanity_impact)}"
        else:
            return self.on_error(game, utterance)

    def on_read(self, game: IFGameEngine, utterance: str):
        if self.builtin.wall.match(utterance) or self.altar.match(utterance) or self.symbols.match(utterance):
            return game.get_dialog("read_wall") + f"\n{self.decrease_sanity(game, 2)}"
        elif self.builtin.book.match(utterance):
            if "book" in self.destroyed:
                return game.get_dialog("destroy_book_aftermath")
            return game.get_dialog("read_book") + f"\n{self.decrease_sanity(game, 3)}"
        else:
            return self.on_error(game, utterance)

    def on_listen(self, game: IFGameEngine, utterance: str):
        if self.builtin.window.match(utterance):
            return game.get_dialog("listen_window")
        elif self.builtin.door.match(utterance):
            return game.get_dialog("listen_door")
        elif self.builtin.wall.match(utterance):
            return game.get_dialog("listen_wall")
        elif self.floor.match(utterance):
            return game.get_dialog("listen_floor")
        elif self.slime.match(utterance):
            return game.get_dialog("listen_slime")
        elif self.cassette.match(utterance):
            if "cassette" in self.destroyed:
                return game.get_dialog("destroy_cassette_aftermath")
            recordings = [l for l in game.dialog_renderer.get_text("listen_cassette").split("\n") if l]
            if self.n_listens >= len(recordings):
                return game.get_dialog("cassette_damaged")
            response = game.get_dialog("listen_cassette_start") + "\n" + recordings[self.n_listens]
            self.n_listens += 1
            # if listened N times start to lose sanity
            if self.n_listens > 5 or self.sanity < self.max_sanity / 3:
                response += "\n" + game.get_dialog("listen_cassette_low_sanity") + "\n" + self.decrease_sanity(game, 1)
            return response
        else:
            return game.get_dialog("listen_room")

    def on_smell(self, game: IFGameEngine, utterance: str):
        if self.builtin.painting.match(utterance):
            return game.get_dialog("smell_painting")
        elif self.cassette.match(utterance):
            return game.get_dialog("smell_cassette")
        elif self.builtin.mirror.match(utterance):
            return game.get_dialog("smell_mirror")
        elif self.builtin.window.match(utterance):
            return game.get_dialog("smell_window")
        elif self.builtin.door.match(utterance):
            return game.get_dialog("smell_door")
        elif self.builtin.wall.match(utterance):
            response = game.get_dialog("smell_wall")
            return f"{response}\n{self.decrease_sanity(game, 1)}"
        elif self.floor.match(utterance):
            return game.get_dialog("smell_floor")
        elif self.builtin.key.match(utterance):
            return game.get_dialog("smell_key")
        elif self.builtin.book.match(utterance):
            return game.get_dialog("smell_book")
        elif self.altar.match(utterance):
            return game.get_dialog("smell_altar")
        elif self.slime.match(utterance):
            return game.get_dialog("smell_slime")
        else:
            return game.get_dialog("smell_room")


class EldritchEscape(IFGameEngine):
    def __init__(self, locale_directory: str, lang: str = "en",
                 on_input: GetUserInputHandler = lambda g, u: input(u),
                 on_print: PrintOutputHandler = lambda g, u: print(u)):
        # on_input and on_print can be used to e.g. wrap the game in a voice interface
        dialog_directory = os.path.join(locale_directory, lang, "dialogs")
        dialog_renderer = DialogRenderer(dialog_directory)
        default_response = dialog_renderer.get_dialog("default") + "\n" + dialog_renderer.get_dialog("help_commands")

        room = TheCursedRoom(locale_folder=locale_directory, lang=lang, default_response=default_response)

        callbacks = GameHandlers(on_end=self.on_end, on_start=self.on_start,
                                 on_win=self.on_win, on_lose=self.on_lose,
                                 is_loss=self.is_loss, is_win=self.is_win,
                                 end_turn=self.on_end_turn,
                                 on_input=on_input, on_print=on_print)
        super().__init__(dialog_renderer=dialog_renderer, scenes=[room], handlers=callbacks)

    def on_end_turn(self, game: IFGameEngine):
        # destroying the mirror stops random events
        if "mirror" not in game.active_scene.destroyed:
            game.speak_dialog('random_event')
            # random chance of decreasing sanity
            if random.randint(1, 50) % 4 == 0:
                game.print(game.active_scene.decrease_sanity(game, 1))

    def on_win(self, game: IFGameEngine):
        game.speak_dialog("win")

    def on_lose(self, game: IFGameEngine):
        game.speak_dialog("lose")

    def on_start(self, game: IFGameEngine):
        text = game.dialog_renderer.get_text("intro")
        game.print(text)

    def on_end(self, game: IFGameEngine):
        game.speak_dialog("game_over")

    def is_win(self, game: IFGameEngine) -> bool:
        return not game.running.is_set()

    def is_loss(self, game: IFGameEngine) -> bool:
        current_scene: TheCursedRoom = game.active_scene
        if hasattr(current_scene, 'sanity') and current_scene.sanity <= 0:
            return True  # Sanity loss condition
        return False


if __name__ == "__main__":
    # TODO lang from argparse
    EldritchEscape(locale_directory=os.path.dirname(__file__), lang="en").run()
