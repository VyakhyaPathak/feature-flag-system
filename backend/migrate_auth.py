from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(150),
            role VARCHAR(30) NOT NULL DEFAULT 'member',
            created_at TIMESTAMP DEFAULT now()
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
    conn.commit()

print("Auth migration complete: users table ready.")
