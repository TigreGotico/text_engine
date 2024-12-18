# Text Engine

`text_engine` is an interactive fiction game engine designed to create text-based games with flexible scenes, objects, and intents. It allows developers to define game logic with custom event handlers, manage scenes, objects, and interactions, and parse user inputs for intents. It is extendable with custom logic for handling inputs and outputs.

## Features

- **Scenes and Game Objects**: Easily define scenes with interactive objects, allowing players to engage with the game world.
- **Intent Parsing**: Integrate intents for objects and scenes to handle user interactions naturally.
- **Game Handlers**: Customize the game flow by defining handlers for various events such as game start, win/loss conditions, and turns.
- **Dialog System**: Optionally integrate a dialog renderer to manage and display text-based dialogues.
- **Multithreading**: The game engine runs in a separate thread for asynchronous input handling and smooth gameplay experience.

## Installation

You can install the `text_engine` package using `pip`:

```bash
pip install text_engine
```

## Components

### 1. `GameHandlers`
A collection of callbacks for different game events:
- **is_win**: Determines if the game is won.
- **is_loss**: Determines if the game is lost.
- **on_start**: Triggered before the first turn.
- **on_win**, **on_lose**: Triggered on winning/losing.
- **on_end**: Triggered after the game ends.
- **before_turn**, **end_turn**, **after_turn**: Triggered before, after, and during each game turn.
- **before_interaction**, **after_interaction**: Triggered before and after user input.
- **on_input**, **on_print**: Custom handlers for gathering input and printing output.

### 2. `GameIntents`
Handles the parsing of player input to predict intents for scenes and objects in the game.

- **intents**: A list of `KeywordIntent` objects.
- **parser**: An `IntentEngine` for parsing intents.
- **predict(utterance)**: Predicts the intent for a given utterance.

### 3. `GameScene`
Represents a scene in the game, which can contain interactive objects. Each scene:
- Has a **description**.
- Contains **game objects** that can be interacted with.
- Optionally integrates **GameIntents** to handle interactions with the scene.

### 4. `GameObject`
Represents an object within a scene. Each object:
- Has a **name** and associated **intent handlers**.
- Defines a **default dialog** when no intent matches the user's input.

### 5. `IFGameEngine`
The core game engine that manages scenes, objects, and game flow. It:
- Runs the game loop on a separate thread.
- Handles scene transitions, user input, and printing output.
- Supports multithreading for asynchronous game processing.

### 6. `DialogRenderer`
A class that manages game dialogues, providing functionality to retrieve and speak specific dialogs.


## Customization

You can customize the game loop by providing your own input and output handlers in the `GameHandlers`. 

This flexibility allows you to integrate the engine into different environments, such as a command-line interface, a web server, or a graphical user interface.

## Contributing

Feel free to fork the repository and submit pull requests. All contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.