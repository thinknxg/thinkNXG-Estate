#!/bin/bash
# Restore the legacy backup into upgrade.test and run the thinkNXG Estate upgrade on it.
source /opt/benchenv.sh
cd /home/claude/frappe-bench
BK=$(ls -t sites/legacy.test/private/backups/*database.sql.gz | head -1)
bench drop-site upgrade.test --db-root-username root --db-root-password root --force --no-backup >/dev/null 2>&1
bench new-site upgrade.test --db-root-username root --db-root-password root --admin-password admin >/dev/null 2>&1
bench --site upgrade.test --force restore $BK --db-root-username root --db-root-password root >/dev/null 2>&1 || { echo RESTORE_FAILED; exit 1; }
echo "import re_core.estate_snapshot_tmp as m; m.run('/home/claude/logs/before.json')" | bench --site upgrade.test console >/dev/null 2>&1
echo "--- installed before: $(bench --site upgrade.test list-apps 2>/dev/null | awk '{print $1}' | tr '\n' ' ')"
echo "--- install-app thinknxg_estate"
bench --site upgrade.test install-app thinknxg_estate 2>&1 | grep -v "Updating DocTypes\|Updating Dashboard\|^$"
echo "--- migrate"
bench --site upgrade.test migrate 2>&1 | grep -iE "error|exception|traceback" | head -5
echo "--- installed after: $(bench --site upgrade.test list-apps 2>/dev/null | awk '{print $1}' | tr '\n' ' ')"
echo "import thinknxg_estate.tests.data_snapshot as m; m.run('/home/claude/logs/after.json')" | bench --site upgrade.test console >/dev/null 2>&1
python3 - <<'PY'
import json
b=json.load(open("/home/claude/logs/before.json")); a=json.load(open("/home/claude/logs/after.json"))
diff={k:(b.get(k),a.get(k)) for k in sorted(set(a)|set(b)) if b.get(k)!=a.get(k)}
print("tables compared:", len(b), "| differences:", diff if diff else "none")
PY
echo "--- legacy app working trees (must be clean):"
for a in re_core re_crm re_portal re_voice; do (cd apps/$a && echo "$a: $(git status --short | grep -v estate_snapshot_tmp | wc -l) changed files"); done
