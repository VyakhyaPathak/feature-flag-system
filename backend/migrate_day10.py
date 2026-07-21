from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE environments ADD COLUMN description TEXT"))
    conn.execute(text("ALTER TABLE environments ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'"))
    conn.commit()

print("Migration done")