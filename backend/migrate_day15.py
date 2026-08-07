from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS flag_key VARCHAR(100)"))
    conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS details TEXT"))

    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_flag_key ON audit_log (flag_key)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_actor ON audit_log (actor)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp)"))

    # flag_id used to be a ForeignKey to flags.id. That would block deleting
    # a flag the moment it had any audit history - exactly backwards, since
    # the audit trail is what should survive a delete. Drop the constraint;
    # flag_key (denormalized, set on every write) is now the durable
    # identifier used for display and filtering.
    conn.execute(text("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_flag_id_fkey"))

    conn.commit()

print("Day 15 migration complete: audit_log.flag_key/details columns + indexes ready, flag_id FK relaxed.")