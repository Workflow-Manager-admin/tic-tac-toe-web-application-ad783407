#!/bin/bash
# Usage: This script initializes and migrates the database schema.
# It should be run from the tic_tac_toe_backend directory.

echo "=== Initializing database migrations directory ==="
export FLASK_APP=app
flask db init

echo "=== Generating migration for current models ==="
flask db migrate -m "Initial migration"

echo "=== Applying migrations ==="
flask db upgrade

echo "Database initialized with tables for users, games, moves, participation, and history."
