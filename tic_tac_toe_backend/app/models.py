from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# PUBLIC_INTERFACE
class User(db.Model):
    """User account for authentication and game participation."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    participations = db.relationship('Participation', back_populates='user')
    moves = db.relationship('Move', back_populates='user')

# PUBLIC_INTERFACE
class Game(db.Model):
    """Tic Tac Toe game instance."""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(16), default='OPEN')  # OPEN, IN_PROGRESS, FINISHED
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    board_state = db.Column(db.String(9), default="         ")  # 9-char string for game state

    participations = db.relationship('Participation', back_populates='game')
    moves = db.relationship('Move', back_populates='game')
    history = db.relationship('GameHistory', back_populates='game', cascade="all, delete-orphan")

# PUBLIC_INTERFACE
class Participation(db.Model):
    """Mapping between user and games (who is in which game, X or O)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    symbol = db.Column(db.String(1), nullable=False)  # 'X' or 'O'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='participations')
    game = db.relationship('Game', back_populates='participations')

# PUBLIC_INTERFACE
class Move(db.Model):
    """Represents a single move in a game."""
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # 0-8 for a Tic Tac Toe cell
    symbol = db.Column(db.String(1), nullable=False)  # 'X' or 'O'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    game = db.relationship('Game', back_populates='moves')
    user = db.relationship('User', back_populates='moves')

# PUBLIC_INTERFACE
class GameHistory(db.Model):
    """Stores completed games for long-term lookup."""
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    board_state = db.Column(db.String(9))  # final board

    game = db.relationship('Game', back_populates='history')
