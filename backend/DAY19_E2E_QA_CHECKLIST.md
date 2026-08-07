# Day 19 — End-to-End QA Checklist

Manual companion to `backend/tests/test_day19_e2e.py`. The automated test
proves the backend modules agree with each other; this checklist proves
the same thing from the dashboard, the way a real user would click
through it — matching "2) Frontend – End-to-End Dashboard Flow" from the
Day 19 plan: **Create Flag → Configure Targeting → Check Evaluation →
View Audit Log → View Analytics**, extended here to also cover Cleanup
(Day 17) and the environment switcher (Day 18 polish).

Run through this once per milestone/demo. Check off each box; anything
that doesn't match "Expected" is a bug to file, not a QA note to ignore.

## Setup
- [ ] Backend running (`uvicorn app.main:app --reload`), all Day 1–19 migrations applied
- [ ] Dashboard running (`npm run dev`), logged in
- [ ] Redis running (`redis-cli ping` → `PONG`)

## 1. Create Flag
- [ ] Sidebar → **Flags** → **+ Create Flag**
- [ ] Create `qa_e2e_test` (Boolean, enabled, default `false`)
- [ ] **Expected:** flag appears in the table immediately, no page refresh needed
- [ ] **Expected:** a green success toast appears
- [ ] Row shows **Type**, **Status** (Live/Off toggle), **Rollout** (`—` — no rollout rule yet), **Source**, **Owner** — all populated, no blank/`undefined` cells

## 2. Configure Targeting
- [ ] Click into `qa_e2e_test` → open its detail page
- [ ] Add your own test user ID to the **user whitelist**
- [ ] Add `beta_users` to **group targeting**
- [ ] Set the **rollout slider** to 50%
- [ ] **Expected:** each change shows a save confirmation and persists after a page refresh
- [ ] Back on the Flags table, **Rollout** column now shows a 50% bar for this flag (Day 18 polish)

## 3. Check Evaluation
- [ ] Open the **Evaluation Test Panel** on the flag detail page
- [ ] Evaluate with your whitelisted user ID → **Expected:** `ENABLED`, reason mentions whitelist
- [ ] Evaluate with a random non-whitelisted, non-group user ID → **Expected:** result reflects the 50% rollout bucket, consistent on repeated calls for the *same* user ID
- [ ] Evaluate the same whitelisted user ID again → **Expected:** near-instant response, `Source: cache`

## 4. View Audit Log
- [ ] Sidebar → **Audit Log**
- [ ] Filter by **Flag Key** = `qa_e2e_test`
- [ ] **Expected:** one `CREATE` entry, one `UPDATE` entry per targeting change made in step 2
- [ ] Click **View Diff** on any entry → **Expected:** readable before/after JSON, not raw unformatted text

## 5. View Analytics
- [ ] Back on the flag detail page, check the **Evaluation Count** chart
- [ ] **Expected:** the evaluations made in step 3 show up (may take up to an hour to bucket if you're relying on the live counter rather than a manual `flush_analytics.py` run — run it manually to confirm the flush path too)

## 6. Cleanup Suggestions (Day 17)
- [ ] Disable `qa_e2e_test` in every environment it exists in
- [ ] Sidebar → **Cleanup**, set **Retention Threshold** to **Any age (0 days)**
- [ ] **Expected:** `qa_e2e_test` appears with `FULLY DISABLED`
- [ ] Click **Mark Reviewed** → **Expected:** row updates to "Reviewed", stat card count increments, a new `UPDATE` audit log entry appears for it

## 7. Environment Switcher (Day 18 — global filtering)
- [ ] Switch environment (top navbar) between Development / Staging / Production
- [ ] **Expected:** Flags, Environments, and Audit Log pages all re-filter to the new environment without a manual refresh
- [ ] **Expected (by design, not a bug):** the **Cleanup** page does *not* change with the environment switcher — cleanup candidacy is evaluated across all environments a flag exists in, so it's intentionally environment-agnostic

## 8. No broken links / state issues
- [ ] Every sidebar item loads without a console error
- [ ] Navigating away from the flag detail page and back doesn't show stale data from a different flag
- [ ] Deleting `qa_e2e_test` removes it from Flags, and it stops appearing in Cleanup on the next scan

---
Cleanup after a run:
```bash
# delete qa_e2e_test from the dashboard, or via the API:
curl -X DELETE http://localhost:8000/flags/{flag_id}
```
