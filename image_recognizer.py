"""
Chess Image Recognition Module
Converts screenshots of chess positions to FEN notation using computer vision.
"""

import os
import base64
from typing import Optional
from openai import OpenAI


class ChessImageRecognizer:
    """
    Recognizes chess positions from screenshots and converts them to FEN notation.
    
    Uses OpenAI's vision capabilities for accurate recognition of chess positions
    from various sources (chess.com, lichess.org, etc.)
    """
    
    def __init__(self):
        self.openai_client = None
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
    
    def recognize(self, image_path: str) -> Optional[str]:
        """
        Recognize a chess position from an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            FEN string representing the position, or None if recognition fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Use OpenAI Vision API for recognition
        if self.openai_client:
            return self._recognize_with_openai(image_path)
        else:
            raise RuntimeError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY in your .env file to enable image recognition."
            )
    
    def _encode_image(self, image_path: str) -> str:
        """Encode an image file to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _recognize_with_openai(self, image_path: str) -> Optional[str]:
        """
        Use OpenAI's vision API to recognize the chess position.
        
        This approach is highly accurate and works with screenshots from:
        - chess.com
        - lichess.org
        - Chess24
        - Physical chess boards (photos)
        - Chess diagrams from books/websites
        """
        
        base64_image = self._encode_image(image_path)
        
        # Determine the image type
        ext = os.path.splitext(image_path)[1].lower()
        media_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }.get(ext, 'image/png')
        
        prompt = """Look at this chess board and output the FEN notation.

Rules:
- White pieces: K Q R B N P (uppercase)
- Black pieces: k q r b n p (lowercase)  
- Empty squares: use numbers 1-8
- Ranks separated by /
- Start from rank 8 (top) to rank 1 (bottom)

Output ONLY the FEN position string, like:
r4rk1/pp3ppp/2p2n2/4p3/3P4/3B1P2/PPP2P2/2KR3R

If you cannot recognize the position, output: CANNOT_RECOGNIZE"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=150,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            
            if "CANNOT_RECOGNIZE" in result:
                return None
            
            # Extract FEN from the response
            fen = self._extract_fen_from_response(result)
            
            if fen and self._validate_fen(fen):
                return fen
            
            return None
            
        except Exception as e:
            print(f"OpenAI recognition error: {e}")
            return None
    
    def _extract_fen_from_response(self, response: str) -> Optional[str]:
        """Extract and clean FEN from the model's response."""
        import re
        
        # Method 1: Look for "FEN:" prefix
        fen_line_match = re.search(r'FEN:\s*(.+)', response, re.IGNORECASE)
        if fen_line_match:
            fen_candidate = fen_line_match.group(1).strip()
            cleaned = self._clean_fen(fen_candidate)
            if self._validate_fen(cleaned):
                return cleaned
        
        # Method 2: Look for a line that looks like a complete FEN
        # FEN pattern: 8 ranks separated by /, followed by turn, castling, etc.
        fen_pattern = r'([rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+)\s+([wb])\s+([KQkq-]+)\s+([a-h][36]|-)\s+(\d+)\s+(\d+)'
        full_match = re.search(fen_pattern, response)
        if full_match:
            return full_match.group(0)
        
        # Method 3: Just find the piece placement and add defaults
        piece_pattern = r'[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+/[rnbqkpRNBQKP1-8]+'
        piece_match = re.search(piece_pattern, response)
        if piece_match:
            piece_placement = piece_match.group(0)
            # Validate that it has correct structure (8 ranks)
            ranks = piece_placement.split('/')
            if len(ranks) == 8:
                # Check each rank sums to 8
                valid = True
                for rank in ranks:
                    total = 0
                    for char in rank:
                        if char.isdigit():
                            total += int(char)
                        else:
                            total += 1
                    if total != 8:
                        valid = False
                        break
                
                if valid:
                    return f"{piece_placement} w - - 0 1"
        
        return None
    
    def _clean_fen(self, fen: str) -> str:
        """Clean up a FEN string by removing extra whitespace and fixing common issues."""
        import re
        
        # Remove any markdown formatting
        fen = fen.replace('`', '').strip()
        
        # Remove any trailing punctuation or extra text
        fen = re.sub(r'[.!?].*$', '', fen).strip()
        
        # Split and clean
        parts = fen.split()
        
        if not parts:
            return fen
        
        # The first part should be the piece placement (contains '/')
        piece_placement = None
        remaining_parts = []
        
        for part in parts:
            if '/' in part and piece_placement is None:
                piece_placement = part
            elif piece_placement is not None:
                remaining_parts.append(part)
        
        if not piece_placement:
            return fen
        
        # Rebuild with defaults
        result_parts = [piece_placement]
        
        # Turn (w or b)
        if len(remaining_parts) > 0 and remaining_parts[0] in ['w', 'b']:
            result_parts.append(remaining_parts[0])
            remaining_parts = remaining_parts[1:]
        else:
            result_parts.append('w')
        
        # Castling
        if len(remaining_parts) > 0 and re.match(r'^[KQkq-]+$', remaining_parts[0]):
            result_parts.append(remaining_parts[0])
            remaining_parts = remaining_parts[1:]
        else:
            result_parts.append('-')
        
        # En passant
        if len(remaining_parts) > 0 and re.match(r'^([a-h][36]|-)$', remaining_parts[0]):
            result_parts.append(remaining_parts[0])
            remaining_parts = remaining_parts[1:]
        else:
            result_parts.append('-')
        
        # Halfmove clock
        if len(remaining_parts) > 0 and remaining_parts[0].isdigit():
            result_parts.append(remaining_parts[0])
            remaining_parts = remaining_parts[1:]
        else:
            result_parts.append('0')
        
        # Fullmove number
        if len(remaining_parts) > 0 and remaining_parts[0].isdigit():
            result_parts.append(remaining_parts[0])
        else:
            result_parts.append('1')
        
        return ' '.join(result_parts[:6])
    
    def _validate_fen(self, fen: str) -> bool:
        """
        Basic validation of a FEN string.
        
        Returns True if the FEN appears to be valid, False otherwise.
        """
        try:
            import chess
            board = chess.Board(fen)
            return True
        except Exception:
            return False
    
    def recognize_from_base64(self, base64_image: str, media_type: str = 'image/png') -> Optional[str]:
        """
        Recognize a chess position from a base64-encoded image.
        
        Args:
            base64_image: Base64-encoded image data
            media_type: MIME type of the image
            
        Returns:
            FEN string representing the position, or None if recognition fails
        """
        if not self.openai_client:
            raise RuntimeError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY in your .env file to enable image recognition."
            )
        
        prompt = """Analyze this chess board image and provide the FEN notation for the position shown.

Please respond with ONLY the complete FEN string with all fields:
<piece_placement> <active_color> <castling> <en_passant> <halfmove> <fullmove>

Example: rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1

If you cannot recognize the position, respond with "CANNOT_RECOGNIZE"."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            
            if result == "CANNOT_RECOGNIZE":
                return None
            
            fen = self._clean_fen(result)
            if self._validate_fen(fen):
                return fen
            
            return None
            
        except Exception as e:
            print(f"OpenAI recognition error: {e}")
            return None

