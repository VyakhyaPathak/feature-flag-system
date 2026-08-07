from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cleanup_candidates (
            id BIGSERIAL PRIMARY KEY,
            flag_key VARCHAR(100) NOT NULL UNIQUE,
            status_type VARCHAR(20) NOT NULL,
            since_date TIMESTAMP NOT NULL,
            days_in_state INTEGER NOT NULL DEFAULT 0,
            environments JSONB NOT NULL DEFAULT '[]',
            last_evaluated_at TIMESTAMP,
            reviewed BOOLEAN NOT NULL DEFAULT false,
            reviewed_at TIMESTAMP,
            reviewed_by VARCHAR(100),
            updated_at TIMESTAMP DEFAULT now()
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cleanup_candidates_flag_key ON cleanup_candidates (flag_key)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cleanup_candidates_status_type ON cleanup_candidates (status_type)"))
    conn.commit()

print("Day 17 migration complete: cleanup_candidates table ready.")
