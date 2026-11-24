"""Usage: shoot.py <site> <outdir> <login:user:pwd|guest> <path>... ; screenshots + console errors."""
import os
import sys, asyncio
from playwright.async_api import async_playwright
site, out, auth, paths = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox", f"--host-resolver-rules=MAP {site} {os.environ.get('SERVER', '127.0.0.1:80')}"])
        ctx = await b.new_context(viewport={"width": 1366, "height": 900}, locale="en-US")
        page = await ctx.new_page()
        errs = []
        page.on("console", lambda m: m.type == "error" and errs.append(m.text[:200]))
        page.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)[:200]))
        if auth != "guest":
            _, u, pw = auth.split(":")
            await page.goto(f"http://{site}/about", wait_until="domcontentloaded")
            st = await page.evaluate("""([u, p]) => fetch('/api/method/login', {method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: new URLSearchParams({usr: u, pwd: p})}).then(r => r.status)""", [u, pw])
            print("login", st)
        for i, path in enumerate(paths):
            errs.clear()
            await page.goto(f"http://{site}{path}", wait_until="networkidle", timeout=45000)
            await page.wait_for_timeout(1500)
            name = f"{out}/{i:02d}.png"
            await page.screenshot(path=name, full_page=True)
            print(path, "->", name, "| errors:", errs[:5])
        await b.close()
asyncio.run(main())
