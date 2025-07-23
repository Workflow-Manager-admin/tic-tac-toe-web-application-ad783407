import os
from flask import request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta

from ..models import db, User, Game, Participation, Move, GameHistory
from ..game_logic import (
    validate_move,
    next_player_symbol,
    apply_move,
    get_winner,
    is_draw,
    get_game_status,
)

blp = Blueprint(
    "API", "api",
    url_prefix="/api",
    description="Main API: user and game endpoints"
)

# --- JWT config ---
JWT_SECRET = os.environ.get("JWT_SECRET", "secret-key")  # SHOULD be set in env in production!
JWT_LIFESPAN_MINUTES = 60

def create_token(user):
    exp = datetime.utcnow() + timedelta(minutes=JWT_LIFESPAN_MINUTES)
    return jwt.encode(
        {"user_id": user.id, "exp": exp},
        JWT_SECRET,
        algorithm="HS256"
    )

def decode_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        return None

def token_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            abort(401, message="Authorization token required")
        token = auth.split(" ")[1]
        payload = decode_token(token)
        if not payload or "user_id" not in payload:
            abort(401, message="Invalid or expired token")
        user = User.query.get(payload["user_id"])
        if not user:
            abort(401, message="User not found")
        request.current_user = user
        return fn(*args, **kwargs)
    return wrapper

# --- Schemas for documentation ---

from marshmallow import Schema, fields, EXCLUDE

class UserSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    id = fields.Integer()
    username = fields.String(required=True)
    email = fields.String(required=True)
    registered_at = fields.DateTime()

class RegisterSchema(Schema):
    username = fields.String(required=True)
    email = fields.String(required=True)
    password = fields.String(required=True, load_only=True)

class LoginSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)

class GameSchema(Schema):
    id = fields.Integer()
    created_at = fields.DateTime()
    status = fields.String()
    creator_id = fields.Integer()
    winner_id = fields.Integer(allow_none=True)
    board_state = fields.String()
    participations = fields.Method("get_participants", dump_only=True)
    def get_participants(self, obj):
        return [{"user_id": p.user_id, "symbol": p.symbol} for p in obj.participations]

class MoveSchema(Schema):
    id = fields.Integer()
    game_id = fields.Integer()
    user_id = fields.Integer()
    position = fields.Integer()
    symbol = fields.String()
    timestamp = fields.DateTime()

class GameHistorySchema(Schema):
    id = fields.Integer()
    game_id = fields.Integer()
    completed_at = fields.DateTime()
    winner_id = fields.Integer(allow_none=True)
    board_state = fields.String()

# --- User Auth Endpoints ---

@blp.route("/register")
class RegisterUser(MethodView):
    """Register a new user."""
    @blp.arguments(RegisterSchema)
    @blp.response(201, UserSchema)
    def post(self, data):
        if User.query.filter((User.username==data["username"])|(User.email==data["email"])).first():
            abort(400, message="Username or email already exists.")
        user = User(
            username=data["username"],
            email=data["email"],
            password_hash=generate_password_hash(data["password"])
        )
        db.session.add(user)
        db.session.commit()
        return user

@blp.route("/login")
class LoginUser(MethodView):
    """Authenticate user, returns JWT."""
    @blp.arguments(LoginSchema)
    def post(self, data):
        user = User.query.filter_by(username=data["username"]).first()
        if not user or not check_password_hash(user.password_hash, data["password"]):
            abort(400, message="Invalid username or password")
        token = create_token(user)
        return jsonify({"token": token})

@blp.route("/logout")
class LogoutUser(MethodView):
    """Logout endpoint (for client, just discard JWT)"""
    @blp.doc(summary="Logout (client-side: just discard JWT)")
    def post(self):
        # JWT logout is stateless (blacklist possible but not required)
        return jsonify({"message": "Successfully logged out"}), 200

# --- Game Endpoints ---

@blp.route("/games")
class GameList(MethodView):
    """Create game or list games (open or by user)."""
    @blp.doc(security=[{"BearerAuth": []}])
    @token_required
    @blp.response(200, GameSchema(many=True))
    def get(self):
        """List open games (exclude finished) or games for current user if ?mine=1."""
        mine = request.args.get("mine")
        if mine == "1":
            uid = request.current_user.id
            games = (
                Game.query.join(Participation)
                .filter(Participation.user_id==uid)
                .order_by(Game.created_at.desc())
                .all()
            )
        else:
            games = Game.query.filter(Game.status != "FINISHED").order_by(Game.created_at.desc()).all()
        return games

    @blp.doc(security=[{"BearerAuth": []}])
    @token_required
    @blp.response(201, GameSchema)
    def post(self):
        """Create a new game (current user as creator, symbol X)."""
        current_user = request.current_user
        game = Game(creator_id=current_user.id, board_state="         ", status="OPEN")
        db.session.add(game)
        db.session.flush()  # to get game.id
        p = Participation(game_id=game.id, user_id=current_user.id, symbol="X")
        db.session.add(p)
        db.session.commit()
        return game

@blp.route("/games/<int:game_id>/join")
class GameJoin(MethodView):
    """Join an open game, as 'O'."""
    @blp.doc(security=[{"BearerAuth": []}])
    @token_required
    @blp.response(200, GameSchema)
    def post(self, game_id):
        game = Game.query.get(game_id)
        cur = request.current_user
        if not game:
            abort(404, message="Game not found")
        if game.status != "OPEN":
            abort(400, message="Game not available for joining")
        if any(p.user_id == cur.id for p in game.participations):
            abort(400, message="Already joined this game")
        if len(game.participations) >= 2:
            abort(400, message="Game already has 2 players")
        p = Participation(game_id=game.id, user_id=cur.id, symbol="O")
        game.status = "IN_PROGRESS"
        db.session.add(p)
        db.session.commit()
        return game

@blp.route("/games/<int:game_id>")
class GameDetail(MethodView):
    """Get details for one game (protected)."""
    @blp.doc(security=[{"BearerAuth": []}])
    @token_required
    @blp.response(200, GameSchema)
    def get(self, game_id):
        game = Game.query.get(game_id)
        if not game:
            abort(404, message="Game not found")
        return game

# --- Move Endpoints ---

class MoveRequestSchema(Schema):
    position = fields.Integer(required=True, validate=lambda p: p in range(9))

@blp.route("/games/<int:game_id>/move")
class GameMove(MethodView):
    """Make a move in a game. Updates board, validates move, checks winner/state."""
    @blp.doc(security=[{"BearerAuth": []}])
    @token_required
    @blp.arguments(MoveRequestSchema)
    @blp.response(200, GameSchema)
    def post(self, data, game_id):
        pos = data["position"]
        game = Game.query.get(game_id)
        current_user = request.current_user

        # Validation
        if not game or game.status not in ("OPEN", "IN_PROGRESS"):
            abort(400, message="Game not open for moves")
        part = Participation.query.filter_by(game_id=game_id, user_id=current_user.id).first()
        if not part:
            abort(403, message="Not a participant of this game")
        if game.status == "OPEN":
            abort(400, message="Game hasn't started (need two players)")

        symbol = part.symbol

        # Fetch all moves for game and determine turn using dedicated logic function
        moves = Move.query.filter_by(game_id=game_id).order_by(Move.timestamp.asc()).all()
        expected_symbol = next_player_symbol(len(moves))
        if symbol != expected_symbol:
            abort(400, message=f"Not your turn. It is {expected_symbol}'s turn.")

        board_state = game.board_state
        if not validate_move(board_state, pos):
            abort(400, message="Cell already occupied or invalid position")

        # Apply move using logic module
        new_board_state = apply_move(board_state, pos, symbol)
        move = Move(game_id=game_id, user_id=current_user.id, position=pos, symbol=symbol)
        game.board_state = new_board_state
        db.session.add(move)

        # Check for winner/draw using logic module
        winner_symbol = get_winner(new_board_state)
        draw = is_draw(new_board_state)

        if winner_symbol:
            game.status = "FINISHED"
            game.winner_id = part.user_id
            db.session.add(GameHistory(game_id=game.id, winner_id=part.user_id, board_state=new_board_state))
        elif draw:
            game.status = "FINISHED"
            db.session.add(GameHistory(game_id=game.id, winner_id=None, board_state=new_board_state))
        else:
            # If still moves left and no winner, mark as in progress
            game.status = get_game_status(new_board_state)

        db.session.commit()
        return game


# --- Game State/History Endpoints ---

@blp.route("/games/me/active")
class MyActiveGames(MethodView):
    """Get 'in progress' or open games for current user."""
    @blp.doc(security=[{"BearerAuth": []}])
    @token_required
    @blp.response(200, GameSchema(many=True))
    def get(self):
        uid = request.current_user.id
        games = (
            Game.query.join(Participation)
            .filter(Participation.user_id==uid)
            .filter(Game.status.in_(["OPEN","IN_PROGRESS"]))
            .order_by(Game.created_at.desc())
            .all()
        )
        return games

@blp.route("/games/me/history")
class MyGameHistory(MethodView):
    @blp.doc(security=[{"BearerAuth": []}])
    @token_required
    @blp.response(200, GameHistorySchema(many=True))
    def get(self):
        uid = request.current_user.id
        games = (
            GameHistory.query
            .join(Game, GameHistory.game_id==Game.id)
            .join(Participation, Participation.game_id==Game.id)
            .filter(Participation.user_id==uid)
            .order_by(GameHistory.completed_at.desc())
            .all()
        )
        return games
