from app.database import SessionLocal
from app import models

db = SessionLocal()

# Reuses user 101 (already whitelisted on your demo flag) and adds a
# couple more IDs so the Group Targeting panel and the Evaluation Test
# Panel's real (non-simulated) group lookup have something meaningful to
# show. Adjust these to match whatever flag/user IDs you're actually
# walking through in the demo.
memberships = [
    ("101", "beta_users"),
    ("101", "internal_team"),
    ("102", "beta_users"),
    ("555", "premium_plan"),
    ("777", "beta_users"),
]

added = 0
for user_id, group_name in memberships:
    exists = db.query(models.UserGroupMembership).filter(
        models.UserGroupMembership.user_id == user_id,
        models.UserGroupMembership.group_name == group_name,
    ).first()
    if not exists:
        db.add(models.UserGroupMembership(user_id=user_id, group_name=group_name))
        added += 1

db.commit()
print(f"Seeded user_group_memberships: {added} new row(s) added, {len(memberships) - added} already existed.")