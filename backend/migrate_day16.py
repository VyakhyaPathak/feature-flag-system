from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS evaluation_analytics (
            id BIGSERIAL PRIMARY KEY,
            flag_key VARCHAR(100) NOT NULL,
            hour_bucket TIMESTAMP NOT NULL,
            count BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT now(),
            CONSTRAINT uq_evaluation_analytics_flag_hour UNIQUE (flag_key, hour_bucket)
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evaluation_analytics_flag_key ON evaluation_analytics (flag_key)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evaluation_analytics_hour_bucket ON evaluation_analytics (hour_bucket)"))
    conn.commit()

print("Day 16 migration complete: evaluation_analytics table ready.")