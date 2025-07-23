# tic-tac-toe-web-application-ad783407

## Database Setup

This backend uses PostgreSQL with SQLAlchemy ORM. 

1. **Set the following environment variables** (in your `.env` or shell):
   ```
   POSTGRES_URL=<your-db-host>
   POSTGRES_USER=<your-db-username>
   POSTGRES_PASSWORD=<your-db-password>
   POSTGRES_DB=<your-db-name>
   POSTGRES_PORT=<your-db-port>
   ```

2. **Install required dependencies:**
   ```
   pip install -r tic_tac_toe_backend/requirements.txt
   ```

3. **Initialize and migrate the database:**
   ```
   cd tic_tac_toe_backend
   bash init_db.sh
   ```

   This sets up all tables: users, games, moves, participation, and game histories.

4. **Development server:**
   ```
   python run.py
   ```