# ♔ Chess Position Analyzer

A beautiful web application that analyzes chess positions from screenshots or FEN codes and provides AI-powered explanations of the best moves.

![Chess Position Analyzer](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- 📷 **Screenshot Recognition**: Upload screenshots from chess.com, lichess.org, or any chess interface
- 📝 **FEN Input**: Directly paste FEN notation from your games
- 🔬 **Deep Analysis**: Powered by Stockfish, one of the strongest chess engines
- 💡 **AI Explanations**: Natural language explanations of why moves are good (using GPT-4)
- 🎨 **Beautiful UI**: Modern, dark-themed interface with interactive chess board

## Quick Start

### Prerequisites

1. **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
2. **Stockfish Chess Engine** - Required for analysis

   ```bash
   # macOS (using Homebrew)
   brew install stockfish

   # Ubuntu/Debian
   sudo apt install stockfish

   # Windows
   # Download from https://stockfishchess.org/download/
   ```

3. **OpenAI API Key** (optional but recommended)
   - Required for screenshot recognition
   - Required for AI-powered move explanations
   - Get your key at [platform.openai.com](https://platform.openai.com/api-keys)

### Installation

1. **Clone or download this repository**

   ```bash
   cd "BAds prototype"
   ```

2. **Create a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Run the application**

   ```bash
   python app.py
   ```

6. **Open in browser**
   
   Navigate to [http://localhost:8080](http://localhost:8080)

## Usage

### Option 1: FEN Code

1. Copy the FEN string from your chess game
2. Paste it into the "FEN Code" input field
3. Click "Analyze Position"

**Example FEN:**
```
r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4
```

### Option 2: Screenshot

1. Take a screenshot of your chess board (works with chess.com, lichess, etc.)
2. Click "Screenshot" tab
3. Drag & drop or click to upload your image
4. Click "Analyze Position"

**Tip:** For best results, capture just the chess board without extra UI elements.

## How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Screenshot    │────▶│  GPT-4 Vision    │────▶│   FEN String    │
│   or FEN Input  │     │  (Recognition)   │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  AI Explanation │◀────│    Stockfish     │◀────│  python-chess   │
│  (GPT-4)        │     │    Analysis      │     │  Board Setup    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

1. **Image Recognition**: Screenshots are analyzed by GPT-4 Vision to extract the chess position
2. **Position Parsing**: FEN is validated and loaded into a chess board representation
3. **Engine Analysis**: Stockfish analyzes the position at configurable depth
4. **Explanation Generation**: GPT-4 explains the best moves in natural language

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the web interface |
| `/api/analyze` | POST | Analyze a position |
| `/api/validate-fen` | POST | Validate a FEN string |
| `/api/health` | GET | Health check |

### Analyze Endpoint

**Request:**
```json
{
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "depth": 20,
    "num_moves": 3
}
```

Or with an image:
```json
{
    "image": "data:image/png;base64,iVBORw0KGgo...",
    "depth": 20,
    "num_moves": 3
}
```

**Response:**
```json
{
    "fen": "...",
    "turn": "white",
    "best_moves": [
        {
            "rank": 1,
            "move": "e2e4",
            "move_san": "e4",
            "score": "+0.35",
            "line": "e4 e5 Nf3 Nc6 Bb5"
        }
    ],
    "explanation": "This position is slightly better for White...",
    "analysis_depth": 20
}
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for vision and explanations | - |
| `STOCKFISH_PATH` | Path to Stockfish binary | Auto-detected |
| `PORT` | Server port | 8080 |
| `DEBUG` | Enable debug mode | false |

## Project Structure

```
BAds prototype/
├── app.py                 # Flask application
├── chess_analyzer.py      # Chess engine integration & explanation generation
├── image_recognizer.py    # Screenshot to FEN conversion
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── README.md             # This file
└── static/
    └── index.html        # Frontend UI
```

## Troubleshooting

### "Stockfish not found"

Make sure Stockfish is installed and accessible:

```bash
# Check if stockfish is in PATH
which stockfish

# Or set the path explicitly in .env
STOCKFISH_PATH=/path/to/stockfish
```

### "OpenAI API key not configured"

Screenshot recognition and AI explanations require an OpenAI API key:

1. Get a key from [platform.openai.com](https://platform.openai.com/api-keys)
2. Add it to your `.env` file: `OPENAI_API_KEY=sk-...`

### Image recognition not working

- Ensure the screenshot clearly shows the chess board
- Avoid capturing UI elements around the board
- Standard chess piece sets work best

## Alternative: Using Leela Chess Zero

While this app uses Stockfish by default (easier to set up), you can modify `chess_analyzer.py` to use Leela Chess Zero instead:

1. Download Leela from [lczero.org](https://lczero.org/)
2. Download a neural network weights file
3. Update the engine path and add the weights parameter

## License

MIT License - feel free to use and modify for your projects.

## Credits

- [Stockfish](https://stockfishchess.org/) - The powerful open-source chess engine
- [python-chess](https://python-chess.readthedocs.io/) - Chess library for Python
- [OpenAI](https://openai.com/) - GPT-4 for explanations and vision capabilities

