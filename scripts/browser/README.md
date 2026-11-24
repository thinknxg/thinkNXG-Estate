# Browser checks (Playwright)

Run against a test or staging copy (they create visitor accounts, enquiries and lease requests).
`SERVER` is where the site is served (default `127.0.0.1:80`); the site name is passed as the
first argument and mapped to that address, so no DNS entry is needed.

```bash
pip install playwright && playwright install chromium
python visitor_flow.py SITE out/        # sign up, save, save search, compare, viewing, lease request, account page
python shoot.py SITE out/ guest /properties "/properties?view=map"          # screenshots + page errors
SHOT_USER=user@example.com SHOT_PWD=... python console_shots.py SITE out/ dashboard,crm   # staff console screens
```

Set the user's language to Arabic to check the right-to-left layout.
