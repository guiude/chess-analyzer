"""
Chess Position Analyzer
A web application that analyzes chess positions from screenshots or FEN codes
and provides natural language explanations of the best moves.
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import base64
import tempfile

from chess_analyzer import ChessAnalyzer
from image_recognizer import ChessImageRecognizer

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize components
analyzer = ChessAnalyzer()
image_recognizer = ChessImageRecognizer()


@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('static', 'index.html')


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Return optimal analysis settings based on server resources."""
    from chess_analyzer import get_optimal_settings
    return jsonify(get_optimal_settings())


@app.route('/api/analyze', methods=['POST'])
def analyze_position():
    """
    Analyze a chess position from either FEN or screenshot.
    
    Request JSON:
    {
        "fen": "optional FEN string",
        "image": "optional base64 encoded image",
        "depth": optional analysis depth (default 20),
        "num_moves": optional number of moves to analyze (default 3),
        "lang": optional language code ("en" or "pt", default "en")
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    fen = data.get('fen')
    image_data = data.get('image')
    depth = data.get('depth', 20)
    num_moves = data.get('num_moves', 3)
    lang = data.get('lang', 'en')
    
    # If image is provided, extract FEN from it
    if image_data and not fen:
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode and save temporarily
            image_bytes = base64.b64decode(image_data)
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            
            try:
                fen = image_recognizer.recognize(tmp_path)
            finally:
                os.unlink(tmp_path)
                
            if not fen:
                return jsonify({"error": "Could not recognize chess position from image"}), 400
                
        except Exception as e:
            return jsonify({"error": f"Image processing error: {str(e)}"}), 400
    
    if not fen:
        return jsonify({"error": "No FEN or image provided"}), 400
    
    # Analyze the position
    try:
        result = analyzer.analyze(fen, depth=depth, num_moves=num_moves, lang=lang)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Analysis error: {str(e)}"}), 400


@app.route('/api/validate-fen', methods=['POST'])
def validate_fen():
    """Validate a FEN string"""
    data = request.get_json()
    fen = data.get('fen', '')
    
    is_valid, message = analyzer.validate_fen(fen)
    return jsonify({"valid": is_valid, "message": message})


@app.route('/api/recognize', methods=['POST'])
def recognize_position():
    """
    Recognize chess position from an image WITHOUT analyzing it.
    Returns just the FEN for user verification.
    
    Request JSON:
    {
        "image": "base64 encoded image"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({"error": "No image provided"}), 400
    
    try:
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode and save temporarily
        image_bytes = base64.b64decode(image_data)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        try:
            fen = image_recognizer.recognize(tmp_path)
        finally:
            os.unlink(tmp_path)
            
        if not fen:
            return jsonify({"error": "Could not recognize chess position from image. Try using Manual Entry instead."}), 400
        
        # Validate the FEN structure (but don't require valid position)
        # Just check it has the right format
        parts = fen.split(' ')
        if len(parts) < 1 or '/' not in parts[0]:
            return jsonify({"error": "Recognition produced invalid format. Try using Manual Entry instead."}), 400
        
        # Determine turn from FEN
        turn = 'white' if len(parts) < 2 or parts[1] == 'w' else 'black'
        
        return jsonify({
            "success": True,
            "fen": fen,
            "turn": turn
        })
        
    except Exception as e:
        return jsonify({"error": f"Image processing error: {str(e)}"}), 400


@app.route('/api/correct-position', methods=['POST'])
def correct_position():
    """
    Apply a text correction to a FEN position and re-analyze.
    
    Request JSON:
    {
        "original_fen": "the FEN that needs correction",
        "correction": "plain English description of the correction",
        "depth": optional analysis depth (default 20),
        "num_moves": optional number of moves to analyze (default 3)
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    original_fen = data.get('original_fen')
    correction = data.get('correction')
    depth = data.get('depth', 20)
    num_moves = data.get('num_moves', 3)
    
    if not original_fen or not correction:
        return jsonify({"error": "Both original_fen and correction are required"}), 400
    
    # Try to apply the correction using OpenAI
    try:
        corrected_fen = apply_fen_correction(original_fen, correction)
        
        if not corrected_fen:
            return jsonify({"error": "Could not apply the correction. Please try editing the FEN directly."}), 400
        
        # Analyze the corrected position
        result = analyzer.analyze(corrected_fen, depth=depth, num_moves=num_moves)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Correction error: {str(e)}"}), 400


def apply_fen_correction(original_fen: str, correction: str) -> str:
    """
    Use OpenAI to apply a text correction to a FEN position.
    
    Returns the corrected FEN string, or None if correction failed.
    """
    import os
    from openai import OpenAI
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        # If no API key, try to parse simple corrections manually
        return parse_simple_correction(original_fen, correction)
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""You are a chess FEN correction assistant. 

Given this FEN position:
{original_fen}

The user says this correction is needed:
"{correction}"

Apply the correction to the FEN and return ONLY the corrected FEN string.

Rules:
- Only change what the user specified
- Keep all other pieces in their original positions
- Maintain valid FEN format
- The FEN has 6 fields separated by spaces: position, turn, castling, en-passant, halfmove, fullmove

Square notation reminder:
- Files: a=1st column (left), h=8th column (right)
- Ranks: 1=bottom (white's back rank), 8=top (black's back rank)
- So h8 is top-right corner, a1 is bottom-left corner

Return ONLY the corrected FEN string, nothing else."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You correct FEN chess positions based on user instructions. Return only the corrected FEN string."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0
        )
        
        corrected_fen = response.choices[0].message.content.strip()
        
        # Validate the corrected FEN
        is_valid, _ = analyzer.validate_fen(corrected_fen)
        if is_valid:
            return corrected_fen
        
        return None
        
    except Exception as e:
        print(f"OpenAI correction error: {e}")
        return parse_simple_correction(original_fen, correction)


def parse_simple_correction(original_fen: str, correction: str) -> str:
    """
    Try to parse simple corrections without AI.
    Handles patterns like "king is on h8 not g8" or "move king from g8 to h8"
    """
    import chess
    import re
    
    try:
        board = chess.Board(original_fen)
        correction_lower = correction.lower()
        
        # Pattern: "X is on Y not Z" or "X should be on Y"
        piece_map = {
            'king': chess.KING, 'queen': chess.QUEEN, 'rook': chess.ROOK,
            'bishop': chess.BISHOP, 'knight': chess.KNIGHT, 'pawn': chess.PAWN
        }
        
        color_map = {
            'white': chess.WHITE, 'black': chess.BLACK
        }
        
        # Try to find piece, color, and squares mentioned
        for piece_name, piece_type in piece_map.items():
            if piece_name in correction_lower:
                # Find squares mentioned (e.g., h8, g8, a1)
                squares = re.findall(r'\b([a-h][1-8])\b', correction_lower)
                
                if len(squares) >= 1:
                    # Determine color from context
                    color = None
                    for color_name, color_val in color_map.items():
                        if color_name in correction_lower:
                            color = color_val
                            break
                    
                    # If no color specified, try to infer from the piece being moved
                    if color is None and len(squares) >= 2:
                        wrong_square = chess.parse_square(squares[1]) if 'not' in correction_lower else chess.parse_square(squares[0])
                        piece_at = board.piece_at(wrong_square)
                        if piece_at and piece_at.piece_type == piece_type:
                            color = piece_at.color
                    
                    if color is not None and len(squares) >= 1:
                        # Find where the piece currently is
                        correct_square = chess.parse_square(squares[0])
                        
                        # Find the wrong square (where the piece currently is incorrectly)
                        if len(squares) >= 2 and 'not' in correction_lower:
                            wrong_square = chess.parse_square(squares[1])
                        else:
                            # Find where this piece type is for this color
                            for sq in chess.SQUARES:
                                p = board.piece_at(sq)
                                if p and p.piece_type == piece_type and p.color == color:
                                    wrong_square = sq
                                    break
                        
                        # Remove piece from wrong square and place on correct square
                        if wrong_square is not None:
                            board.remove_piece_at(wrong_square)
                            board.set_piece_at(correct_square, chess.Piece(piece_type, color))
                            
                            return board.fen()
        
        return None
        
    except Exception as e:
        print(f"Simple correction parse error: {e}")
        return None


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    engine_status = analyzer.check_engine()
    return jsonify({
        "status": "healthy" if engine_status else "degraded",
        "engine_available": engine_status
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

