Industrial Sci-Fi Logic Chamber

An intense, fast-paced reflex and logic puzzle game built using Python and PySide6. Players must process rapidly changing instructions, overcome tricky cognitive traps, and react before the pressure timer runs out.

📸 Overview

Industrial Sci-Fi Logic Chamber tests both your response speed and reading comprehension under pressure. Styled like a retro-futuristic sci-fi terminal panel, the game presents a central big button and dynamic logic prompts.

Some prompts require fast clicks, others require waiting, holding, multi-tapping, or solving subtle trick logic!

✨ Features

Custom GUI Rendering: Built entirely with PySide6's QPainter—featuring custom dynamic animations, procedural industrial bolts, hex grids, gears, hologram scanlines, and fluid pipes.

Dynamic Command Sequence: Procedurally generated sequence featuring over 20+ distinct logic commands and cognitive tricks.

Interactive Mechanics:

Single & Multi-Taps: Double taps, dynamic score-based tap counts, corner counts for geometric shapes, and vowel counting.

Timed Holds: Hold until the button changes color to blue.

Phased Delay Prompts: Wait through phase sequences before hitting "NOW!".

Trick & Paradox Logic: Paradox sequences ("the next statement is a lie"), color tricks ("press the red word"), and reverse rules ("for next 3 commands do opposite").

Pressure Battery Timer: A visual segmented cell battery showing remaining time that dynamic speeds up based on non-press streaks.

Brief Transition Blackouts: Quick screen flashes between steps to keep you on edge.

🛠️ Prerequisites & Installation

Requirements

Python 3.8+

PySide6

Setup Instructions

Clone or Download the Repository:

git clone https://github.com/your-username/industrial-scifi-logic-chamber.git
cd industrial-scifi-logic-chamber


Install Dependencies:
Install required packages via pip:

pip install PySide6


Run the Game:

python main.py


🎮 How to Play

Start: Launch the app to start the game immediately.

Read Carefully: A command appears inside the central interactive button.

Follow Logic, Not Just Words:

PRESS / HIT IT / DOUBLE TAP: Click the button the requested number of times.

DONT PRESS / PRESS 0 TIMES: Wait for the timer to expire without touching the button.

HOLD UNTIL BLUE: Press and hold down the mouse button; release only after the main button turns blue.

WAIT... WAIT... NOW!: Do not click during the wait phases—only click when "NOW!" appears.

COLOR / TRICK PROMPTS: Watch out for misleading text colors, shapes, and logical paradoxes!

Restart: If you fail or fall for a trap, click anywhere on the screen during the Game Over screen to restart.

📁 Project Structure

├── main.py          # Main application file containing game logic, visual rendering, and UI setup
└── README.md        # Project documentation


🚀 Future Roadmap

[ ] Sound FX and ambient industrial audio loop

[ ] High score saving (local JSON or SQLite)

[ ] Difficulty modes (Faster timers, more complex math/logic puzzles)

📜 License

Distributed under the MIT License. Feel free to modify and adapt for personal or commercial projects.
