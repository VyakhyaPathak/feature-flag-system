from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE environments ADD COLUMN IF NOT EXISTS description TEXT"))
    conn.execute(text(
        "ALTER TABLE environments ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'"
    ))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS flag_overrides (
            id SERIAL PRIMARY KEY,
            flag_key VARCHAR(100) NOT NULL,
            environment_id INTEGER NOT NULL REFERENCES environments(id),
            enabled BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            CONSTRAINT uq_flag_override_key_env UNIQUE (flag_key, environment_id)
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_flag_overrides_flag_key ON flag_overrides (flag_key)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_flag_overrides_environment_id ON flag_overrides (environment_id)"))

    conn.commit()

print("Day 10 migration complete: environments.description/status columns + flag_overrides table ready.")