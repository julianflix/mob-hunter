
# Mob Hunters

A Minecraft-inspired game built with Python and portable to web using pygbag.

## Description

Mob Hunters is a Minecraft-inspired game that captures the essence of exploration, and combat in a simplified yet engaging format. The game is designed to be easily portable to web platforms using the pygbag framework, allowing players to enjoy it directly in their browsers without requiring local installation.

## Features

- Minecraft-style gameplay mechanics
- Portable to web using pygbag

## Getting Started

### Prerequisites

- Python 3.x installed on your system
- Basic knowledge of Python development

### Installation

1. Create a Python virtual environment:
   ```bash
   python -m venv mob_hunters_env
   ````

2. Activate the virtual environment:
   - On Windows:
     ```bash
     mob_hunters_env\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source mob_hunters_env/bin/activate
     ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Playing the Game

### Local Play

To play the game locally on your computer, simply run the main game script after installing dependencies.

### Web Play

To play the game in a web browser using pygbag:

1. Copy the `/build/web` folder and `assets` folder to your project directory
2. Access `index.html` to start playing

Example: [https://julianflix.com/mob-hunters/index.html](https://julianflix.com/mob-hunters/index.html)

## Deployment

The game is designed to be easily deployed to web platforms using pygbag. The `/build/web` folder contains all necessary files for web deployment, including the compiled Python code and assets.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by Minecraft gameplay
- Built with Python and pygbag framework
