"""
Chess Position Analyzer Module
Handles chess engine integration and move explanation generation.
"""

import chess
import chess.engine
import os
from typing import Optional, Tuple, List, Dict, Any

def get_memory_mb() -> int:
    """Get available system memory in MB, accounting for container limits."""
    
    # Check for container memory limit first (cgroups v1 and v2)
    cgroup_paths = [
        '/sys/fs/cgroup/memory/memory.limit_in_bytes',  # cgroups v1
        '/sys/fs/cgroup/memory.max',  # cgroups v2
    ]
    
    for cgroup_path in cgroup_paths:
        try:
            with open(cgroup_path, 'r') as f:
                limit = f.read().strip()
                if limit != 'max' and limit.isdigit():
                    limit_mb = int(limit) // (1024 * 1024)
                    # Only use if it's a reasonable limit (not unlimited)
                    if limit_mb < 64000:  # Less than 64GB = real limit
                        return limit_mb
        except:
            pass
    
    # Fallback to psutil
    try:
        import psutil
        return psutil.virtual_memory().total // (1024 * 1024)
    except ImportError:
        pass
    
    # Final fallback
    return 512

def is_cloud_environment() -> bool:
    """Detect if running in a cloud/container environment."""
    cloud_indicators = [
        'RENDER',           # Render.com
        'RAILWAY_ENVIRONMENT',  # Railway
        'HEROKU',           # Heroku
        'DYNO',             # Heroku
        'FLY_APP_NAME',     # Fly.io
        'VERCEL',           # Vercel
        'AWS_LAMBDA_FUNCTION_NAME',  # AWS Lambda
        'GOOGLE_CLOUD_PROJECT',  # Google Cloud
    ]
    return any(os.environ.get(var) for var in cloud_indicators)

def get_optimal_settings() -> dict:
    """Get optimal Stockfish settings based on available memory."""
    
    # Force conservative settings on known cloud platforms
    if is_cloud_environment():
        print("Cloud environment detected - using conservative memory settings")
        return {
            "hash": 16,
            "threads": 1,
            "max_depth": 20,
            "default_depth": 16,
            "memory_mb": 512,
            "cloud_mode": True
        }
    
    memory_mb = get_memory_mb()
    
    if memory_mb >= 8000:  # 8GB+ (good desktop/laptop)
        return {
            "hash": 256,
            "threads": 4,
            "max_depth": 30,
            "default_depth": 22,
            "memory_mb": memory_mb,
            "cloud_mode": False
        }
    elif memory_mb >= 4000:  # 4GB+ (modest machine)
        return {
            "hash": 128,
            "threads": 2,
            "max_depth": 25,
            "default_depth": 20,
            "memory_mb": memory_mb,
            "cloud_mode": False
        }
    elif memory_mb >= 1000:  # 1GB+ (limited VPS)
        return {
            "hash": 64,
            "threads": 1,
            "max_depth": 22,
            "default_depth": 18,
            "memory_mb": memory_mb,
            "cloud_mode": False
        }
    else:  # <1GB (Render free tier, etc.)
        return {
            "hash": 16,
            "threads": 1,
            "max_depth": 20,
            "default_depth": 16,
            "memory_mb": memory_mb,
            "cloud_mode": False
        }

# Get settings at module load
OPTIMAL_SETTINGS = get_optimal_settings()
from openai import OpenAI


class ChessAnalyzer:
    """Analyzes chess positions using Stockfish and generates explanations."""
    
    def __init__(self):
        self.engine_path = self._find_engine()
        self.engine = None
        self.openai_client = None
        
        # Initialize OpenAI if API key is available
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
    
    def _find_engine(self) -> Optional[str]:
        """Find Stockfish engine on the system."""
        # Common locations for Stockfish
        home = os.path.expanduser('~')
        app_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(app_dir, 'bin', 'stockfish'),  # Project bin folder (Render)
            os.path.join(home, 'bin', 'stockfish'),  # Home bin folder
            './bin/stockfish',  # Relative path
            '/usr/local/bin/stockfish',
            '/usr/bin/stockfish',
            '/usr/games/stockfish',
            '/opt/homebrew/bin/stockfish',
            'stockfish',  # If in PATH
            os.path.join(app_dir, 'stockfish'),
            os.path.join(app_dir, 'engines', 'stockfish'),
        ]
        
        # Check environment variable first
        env_path = os.environ.get('STOCKFISH_PATH')
        if env_path:
            possible_paths.insert(0, env_path)
        
        for path in possible_paths:
            if os.path.isfile(path) or self._check_command_exists(path):
                return path
        
        return None
    
    def _check_command_exists(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        import shutil
        return shutil.which(cmd) is not None
    
    def _get_engine(self) -> chess.engine.SimpleEngine:
        """Get or create the chess engine instance."""
        if self.engine is None:
            if not self.engine_path:
                raise RuntimeError(
                    "Stockfish not found. Please install Stockfish:\n"
                    "  macOS: brew install stockfish\n"
                    "  Ubuntu: sudo apt install stockfish\n"
                    "  Or set STOCKFISH_PATH environment variable"
                )
            self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            # Configure based on available system memory
            self.engine.configure({
                "Hash": OPTIMAL_SETTINGS["hash"],
                "Threads": OPTIMAL_SETTINGS["threads"]
            })
            memory_mb = get_memory_mb()
            print(f"Stockfish configured: {memory_mb}MB RAM detected → Hash={OPTIMAL_SETTINGS['hash']}MB, Threads={OPTIMAL_SETTINGS['threads']}")
        return self.engine
    
    def check_engine(self) -> bool:
        """Check if the chess engine is available."""
        try:
            engine = self._get_engine()
            return engine is not None
        except Exception:
            return False
    
    def validate_fen(self, fen: str) -> Tuple[bool, str]:
        """
        Validate a FEN string.
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            board = chess.Board(fen)
            if board.is_valid():
                return True, "Valid FEN"
            else:
                return False, "Invalid board position"
        except ValueError as e:
            return False, f"Invalid FEN: {str(e)}"
    
    def analyze(self, fen: str, depth: int = None, num_moves: int = 3, lang: str = 'en') -> Dict[str, Any]:
        """
        Analyze a chess position.
        
        Depth is automatically optimized based on available system memory.
        
        Args:
            fen: FEN string representing the position
            depth: Analysis depth (default 20)
            num_moves: Number of top moves to analyze (default 3)
            lang: Language code for explanations ('en' or 'pt')
            
        Returns:
            Dictionary with analysis results and explanations
        """
        # Validate FEN
        is_valid, message = self.validate_fen(fen)
        if not is_valid:
            raise ValueError(message)
        
        # Use optimal depth based on system memory, with user override capped
        if depth is None:
            depth = OPTIMAL_SETTINGS["default_depth"]
        else:
            depth = min(depth, OPTIMAL_SETTINGS["max_depth"])
        
        board = chess.Board(fen)
        engine = self._get_engine()
        
        # Get multi-PV analysis (multiple best moves)
        analysis_results = []
        
        with engine.analysis(board, chess.engine.Limit(depth=depth), multipv=num_moves) as analysis:
            for info in analysis:
                if 'multipv' in info:
                    pv_index = info['multipv'] - 1
                    
                    # Extend results list if needed
                    while len(analysis_results) <= pv_index:
                        analysis_results.append({})
                    
                    result = analysis_results[pv_index]
                    
                    if 'score' in info:
                        score = info['score'].white()
                        result['score'] = self._format_score(score)
                        result['score_value'] = score.score(mate_score=10000) if score.score() is not None else (10000 if score.mate() > 0 else -10000)
                    
                    if 'pv' in info:
                        result['pv'] = [move.uci() for move in info['pv'][:10]]
                        result['pv_san'] = self._pv_to_san(board, info['pv'][:10])
                    
                    if 'depth' in info:
                        result['depth'] = info['depth']
        
        # Format the best moves
        best_moves = []
        is_white_turn = board.turn  # True if white to move
        
        for i, result in enumerate(analysis_results):
            if result and 'pv' in result:
                move = result['pv'][0]
                move_san = result['pv_san'][0] if result['pv_san'] else move
                
                # Raw score (from White's perspective) - used for template logic
                raw_score_value = result.get('score_value', 0)
                raw_score = result.get('score', 'N/A')
                
                # Display score (from moving side's perspective)
                # Flip the sign if it's Black's turn so positive = good for the moving side
                display_score_value = raw_score_value if is_white_turn else -raw_score_value
                display_score = self._format_display_score(raw_score, is_white_turn)
                
                best_moves.append({
                    'rank': i + 1,
                    'move': move,
                    'move_san': move_san,
                    'score': display_score,  # Now from moving side's perspective
                    'score_value': display_score_value,  # Now from moving side's perspective
                    'raw_score_value': raw_score_value,  # Keep original for template logic
                    'line': ' '.join(result['pv_san'][:5]),
                    'full_line': result['pv_san']
                })
        
        # Generate position context
        position_context = self._get_position_context(board)
        
        # Generate natural language explanation
        explanation = self._generate_explanation(board, best_moves, position_context, lang)
        
        return {
            'fen': fen,
            'turn': 'white' if board.turn else 'black',
            'position_context': position_context,
            'best_moves': best_moves,
            'explanation': explanation,
            'analysis_depth': depth
        }
    
    def _format_display_score(self, raw_score: str, is_white_turn: bool) -> str:
        """Format score from the moving side's perspective."""
        if raw_score == 'N/A':
            return raw_score
        
        # Handle mate scores
        if raw_score.startswith('Mate in'):
            # Mate in X means White is winning
            if is_white_turn:
                return raw_score  # White to move and winning - keep as is
            else:
                # Black to move but White is winning - flip to "Mated in"
                moves = raw_score.replace('Mate in ', '')
                return f"Mated in {moves}"
        elif raw_score.startswith('Mated in'):
            # Mated in X means White is losing
            if is_white_turn:
                return raw_score  # White to move and losing - keep as is
            else:
                # Black to move and White is losing = Black is winning
                moves = raw_score.replace('Mated in ', '')
                return f"Mate in {moves}"
        
        # Handle centipawn scores (e.g., "+1.25" or "-0.50")
        try:
            value = float(raw_score)
            display_value = value if is_white_turn else -value
            return f"{display_value:+.2f}"
        except ValueError:
            return raw_score
    
    def _format_score(self, score) -> str:
        """Format a chess score for display."""
        if score.is_mate():
            mate_in = score.mate()
            if mate_in > 0:
                return f"Mate in {mate_in}"
            else:
                return f"Mated in {abs(mate_in)}"
        else:
            cp = score.score()
            if cp is not None:
                pawns = cp / 100.0
                sign = '+' if pawns >= 0 else ''
                return f"{sign}{pawns:.2f}"
            return "N/A"
    
    def _pv_to_san(self, board: chess.Board, pv: List[chess.Move]) -> List[str]:
        """Convert a PV (list of moves) to SAN notation."""
        san_moves = []
        temp_board = board.copy()
        
        for move in pv:
            try:
                san_moves.append(temp_board.san(move))
                temp_board.push(move)
            except Exception:
                break
        
        return san_moves
    
    def _get_position_context(self, board: chess.Board) -> Dict[str, Any]:
        """Extract contextual information about the position."""
        context = {
            'is_check': board.is_check(),
            'is_checkmate': board.is_checkmate(),
            'is_stalemate': board.is_stalemate(),
            'can_castle_kingside_white': board.has_kingside_castling_rights(chess.WHITE),
            'can_castle_queenside_white': board.has_queenside_castling_rights(chess.WHITE),
            'can_castle_kingside_black': board.has_kingside_castling_rights(chess.BLACK),
            'can_castle_queenside_black': board.has_queenside_castling_rights(chess.BLACK),
            'material_balance': self._calculate_material_balance(board),
            'move_number': board.fullmove_number,
            'legal_moves_count': len(list(board.legal_moves)),
        }
        
        # Detect game phase
        piece_count = len(board.piece_map())
        if piece_count > 24:
            context['phase'] = 'opening'
        elif piece_count > 12:
            context['phase'] = 'middlegame'
        else:
            context['phase'] = 'endgame'
        
        return context
    
    def _calculate_material_balance(self, board: chess.Board) -> Dict[str, Any]:
        """Calculate material balance for both sides."""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0
        }
        
        white_material = 0
        black_material = 0
        piece_counts = {'white': {}, 'black': {}}
        
        piece_names = {
            chess.PAWN: 'pawns',
            chess.KNIGHT: 'knights',
            chess.BISHOP: 'bishops',
            chess.ROOK: 'rooks',
            chess.QUEEN: 'queens'
        }
        
        for square, piece in board.piece_map().items():
            value = piece_values.get(piece.piece_type, 0)
            name = piece_names.get(piece.piece_type, 'kings')
            
            if piece.color == chess.WHITE:
                white_material += value
                piece_counts['white'][name] = piece_counts['white'].get(name, 0) + 1
            else:
                black_material += value
                piece_counts['black'][name] = piece_counts['black'].get(name, 0) + 1
        
        return {
            'white': white_material,
            'black': black_material,
            'balance': white_material - black_material,
            'piece_counts': piece_counts
        }
    
    def _generate_explanation(
        self, 
        board: chess.Board, 
        best_moves: List[Dict], 
        context: Dict[str, Any],
        lang: str = 'en'
    ) -> str:
        """Generate a natural language explanation of the position and best moves."""
        
        # If OpenAI is available, use it for sophisticated explanations
        if self.openai_client and best_moves:
            return self._generate_llm_explanation(board, best_moves, context, lang)
        
        # Fallback to template-based explanation
        return self._generate_template_explanation(board, best_moves, context, lang)
    
    def _generate_llm_explanation(
        self, 
        board: chess.Board, 
        best_moves: List[Dict], 
        context: Dict[str, Any],
        lang: str = 'en'
    ) -> str:
        """Generate explanation using OpenAI."""
        
        turn = "White" if board.turn else "Black"
        if lang == 'pt':
            turn = "Brancas" if board.turn else "Pretas"
        
        moves_text = ""
        for move in best_moves[:3]:
            moves_text += f"\n- {move['move_san']} (eval: {move['score']}): {move['line']}"
        
        material = context['material_balance']
        if material['balance'] > 0:
            material_desc = f"White is up by {material['balance']} pawns worth of material"
        elif material['balance'] < 0:
            material_desc = f"Black is up by {abs(material['balance'])} pawns worth of material"
        else:
            material_desc = "Material is equal"
        
        # System message with language instruction
        if lang == 'pt':
            system_message = "Você é um treinador de xadrez experiente fornecendo análise de posições. Seja conciso mas completo. Foque em explicar as ideias principais por trás dos lances, não apenas listar variantes. IMPORTANTE: Responda SEMPRE em Português do Brasil."
        else:
            system_message = "You are an expert chess coach providing position analysis. Be concise but thorough. Focus on explaining the key ideas behind the moves rather than just listing variations."
        
        prompt = f"""Analyze this chess position and explain the best moves in a clear, instructive way.

Position (FEN): {board.fen()}
Turn: {turn} to move
Game phase: {context['phase']}
Material: {material_desc}
{"White is in check!" if context['is_check'] and board.turn else "Black is in check!" if context['is_check'] else ""}

Top engine moves:{moves_text}

Please provide:
1. A brief assessment of the position (who stands better and why)
2. An explanation of why the top move is best
3. What the main strategic or tactical ideas are
4. What to avoid and why

Keep the explanation clear and accessible, suitable for intermediate players. Use chess notation where helpful."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": system_message
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            # Fallback to template if API fails
            note = "(Note: AI explanation unavailable)" if lang == 'en' else "(Nota: explicação da IA indisponível)"
            return self._generate_template_explanation(board, best_moves, context, lang) + f"\n\n{note}: {str(e)}"
    
    def _generate_template_explanation(
        self, 
        board: chess.Board, 
        best_moves: List[Dict], 
        context: Dict[str, Any],
        lang: str = 'en'
    ) -> str:
        """Generate a template-based explanation without LLM."""
        
        lines = []
        
        # Translations
        if lang == 'pt':
            turn = "Brancas" if board.turn else "Pretas"
            opponent = "Pretas" if board.turn else "Brancas"
            txt = {
                'position_assessment': '**Avaliação da Posição**',
                'turn_to_move': f"É a vez das {turn} jogarem. O jogo está na fase de {self._translate_phase(context['phase'], lang)}.",
                'material_advantage': lambda side, n: f"{side} têm vantagem material de {n} peão(s).",
                'material_equal': "O material está igual.",
                'in_check': f"⚠️ **{turn} estão em xeque!** A prioridade imediata é escapar do xeque.",
                'checkmate': f"♔ **Xeque-mate!** {'Pretas' if board.turn else 'Brancas'} vencem!",
                'stalemate': "**Afogamento** - O jogo é empate.",
                'analysis_title': '**Análise dos Lances Principais**',
                'best_move': 'Melhor lance',
                'second_best': 'Segundo melhor',
                'third_best': 'Terceiro melhor',
                'forced_mate': 'Este lance leva a um **xeque-mate forçado**!',
                'getting_mated': f'⚠️ Apesar de ser a melhor opção, {turn} serão xeque-mateadas. A posição está perdida.',
                'decisive_advantage': f'{turn} obtêm uma **vantagem decisiva** com este lance. A posição fica ganha.',
                'clear_advantage': f'Este lance dá a {turn} uma **vantagem clara**. A posição é favorável.',
                'slight_edge': f'{turn} mantêm uma **ligeira vantagem** com este lance.',
                'losing': f'⚠️ Mesmo com o melhor jogo, {turn} estão em **posição perdida**.',
                'worse': f'⚠️ {turn} estão **piores** aqui, mas este lance limita os danos.',
                'opponent_edge': f'{opponent} têm ligeira vantagem, mas a posição continua jogável.',
                'equal': 'A posição é **aproximadamente igual** após este lance.',
                'why_sequence': '**Por que esta sequência?**',
                'after_move': 'Após',
                'expected_response': 'a resposta esperada é',
                'game_continues': 'O jogo provavelmente continuaria:',
                'followed_by': 'seguido de',
                'further_moves': 'Lances seguintes nesta linha:',
                'strategic_title': '**Considerações Estratégicas**',
                'opening_advice': '• Na abertura, foque no desenvolvimento das peças, controle do centro e segurança do rei.',
                'middlegame_advice': '• No meio-jogo, busque oportunidades táticas e melhore a coordenação das peças.',
                'endgame_advice': '• No final, a atividade do rei e a promoção de peões são fatores críticos.',
                'can_castle': 'ainda podem rocar',
                'api_tip': '*Para insights estratégicos mais detalhados com explicações de motivos táticos, adicione sua chave de API do OpenAI.*'
            }
        else:
            turn = "White" if board.turn else "Black"
            opponent = "Black" if board.turn else "White"
            txt = {
                'position_assessment': '**Position Assessment**',
                'turn_to_move': f"It's {turn}'s turn to move. The game is in the {context['phase']}.",
                'material_advantage': lambda side, n: f"{side} has a material advantage of {n} pawn(s) worth of material.",
                'material_equal': "Material is equal.",
                'in_check': f"⚠️ **{turn} is in check!** The immediate priority is to escape the check.",
                'checkmate': f"♔ **Checkmate!** {'Black' if board.turn else 'White'} wins!",
                'stalemate': "**Stalemate** - The game is a draw.",
                'analysis_title': '**Analysis of Key Moves**',
                'best_move': 'Best move',
                'second_best': 'Second best',
                'third_best': 'Third best',
                'forced_mate': 'This move leads to a **forced checkmate**!',
                'getting_mated': f'⚠️ Despite being the best option, {turn} is getting checkmated. The position is lost.',
                'decisive_advantage': f'{turn} gains a **decisive advantage** with this move. The position becomes winning.',
                'clear_advantage': f'This move gives {turn} a **clear advantage**. The position is favorable.',
                'slight_edge': f'{turn} maintains a **slight edge** with this move.',
                'losing': f'⚠️ Even with the best play, {turn} is in a **losing position**.',
                'worse': f'⚠️ {turn} is **worse** here, but this move limits the damage.',
                'opponent_edge': f'{opponent} has a slight edge, but the position remains playable.',
                'equal': 'The position is **roughly equal** after this move.',
                'why_sequence': '**Why this sequence?**',
                'after_move': 'After',
                'expected_response': 'the expected response is',
                'game_continues': 'The game would likely continue:',
                'followed_by': 'followed by',
                'further_moves': 'Further moves in this line:',
                'strategic_title': '**Strategic Considerations**',
                'opening_advice': '• In the opening, focus on piece development, controlling the center, and king safety.',
                'middlegame_advice': '• In the middlegame, look for tactical opportunities and improve piece coordination.',
                'endgame_advice': '• In the endgame, king activity and pawn promotion become critical factors.',
                'can_castle': 'can still castle',
                'api_tip': '*For more detailed strategic insights with explanations of tactical motifs, add your OpenAI API key.*'
            }
        
        # Position assessment
        lines.append(txt['position_assessment'])
        lines.append(txt['turn_to_move'])
        
        # Material balance
        material = context['material_balance']
        if material['balance'] > 0:
            side = "White" if lang == 'en' else "Brancas"
            lines.append(txt['material_advantage'](side, material['balance']))
        elif material['balance'] < 0:
            side = "Black" if lang == 'en' else "Pretas"
            lines.append(txt['material_advantage'](side, abs(material['balance'])))
        else:
            lines.append(txt['material_equal'])
        
        # Check status
        if context['is_check']:
            lines.append(txt['in_check'])
        if context['is_checkmate']:
            lines.append(txt['checkmate'])
            return "\n".join(lines)
        if context['is_stalemate']:
            lines.append(txt['stalemate'])
            return "\n".join(lines)
        
        lines.append("")
        
        # Best moves with detailed explanations
        if best_moves:
            lines.append(txt['analysis_title'])
            
            for move in best_moves[:3]:
                rank_label = [txt['best_move'], txt['second_best'], txt['third_best']][move['rank'] - 1] if move['rank'] <= 3 else f"#{move['rank']}"
                
                eval_label = "Evaluation" if lang == 'en' else "Avaliação"
                lines.append(f"\n**{rank_label}: `{move['move_san']}`** ({eval_label}: {move['score']})")
                
                # Explain the evaluation (use display score which is from moving side's perspective)
                # Positive = good for the side to move, Negative = bad for the side to move
                display_score_value = move['score_value']
                
                if move['score'].startswith('Mate in'):
                    lines.append(txt['forced_mate'])
                elif move['score'].startswith('Mated in'):
                    lines.append(txt['getting_mated'])
                elif display_score_value > 300:
                    lines.append(txt['decisive_advantage'])
                elif display_score_value > 100:
                    lines.append(txt['clear_advantage'])
                elif display_score_value > 30:
                    lines.append(txt['slight_edge'])
                elif display_score_value < -300:
                    lines.append(txt['losing'])
                elif display_score_value < -100:
                    lines.append(txt['worse'])
                elif display_score_value < -30:
                    lines.append(txt['opponent_edge'])
                else:
                    lines.append(txt['equal'])
                
                # Explain the continuation
                full_line = move.get('full_line', [])
                if len(full_line) >= 2:
                    lines.append(f"\n{txt['why_sequence']}")
                    lines.append(f"{txt['after_move']} `{full_line[0]}`, {txt['expected_response']} `{full_line[1]}`.")
                    if len(full_line) >= 4:
                        lines.append(f"{txt['game_continues']} `{full_line[2]}` {txt['followed_by']} `{full_line[3]}`.")
                    if len(full_line) >= 5:
                        remaining = ', '.join(f'`{m}`' for m in full_line[4:7])
                        lines.append(f"{txt['further_moves']} {remaining}")
        
        lines.append("")
        
        # Add strategic hints based on position
        lines.append(txt['strategic_title'])
        if context['phase'] == 'opening':
            lines.append(txt['opening_advice'])
        elif context['phase'] == 'middlegame':
            lines.append(txt['middlegame_advice'])
        else:
            lines.append(txt['endgame_advice'])
        
        # Castling rights info
        if context['phase'] in ['opening', 'middlegame']:
            castle_info = []
            white_label = "White" if lang == 'en' else "Brancas"
            black_label = "Black" if lang == 'en' else "Pretas"
            if context['can_castle_kingside_white'] or context['can_castle_queenside_white']:
                castle_info.append(f"{white_label} {txt['can_castle']}")
            if context['can_castle_kingside_black'] or context['can_castle_queenside_black']:
                castle_info.append(f"{black_label} {txt['can_castle']}")
            if castle_info:
                and_word = " and " if lang == 'en' else " e "
                lines.append(f"• {and_word.join(castle_info)}.")
        
        lines.append("")
        lines.append(txt['api_tip'])
        
        return "\n".join(lines)
    
    def _translate_phase(self, phase: str, lang: str) -> str:
        """Translate game phase to the specified language."""
        if lang == 'pt':
            phases = {'opening': 'abertura', 'middlegame': 'meio-jogo', 'endgame': 'final'}
            return phases.get(phase, phase)
        return phase
    
    def __del__(self):
        """Clean up engine on destruction."""
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass

