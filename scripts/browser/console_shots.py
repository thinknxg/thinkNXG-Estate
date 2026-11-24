import asyncio, sys
from playwright.async_api import async_playwright
import os
site, out = sys.argv[1], sys.argv[2]
USER, PWD = os.environ.get("SHOT_USER", "Administrator"), os.environ.get("SHOT_PWD", "admin"); screens = sys.argv[3].split(","); width = int(sys.argv[4]) if len(sys.argv) > 4 else 1366
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox", f"--host-resolver-rules=MAP {site} {os.environ.get('SERVER', '127.0.0.1:80')}"])
        page = await (await b.new_context(viewport={"width": width, "height": 900})).new_page()
        errs = []; page.on("pageerror", lambda e: errs.append(str(e)[:160]))
        await page.goto(f"http://{site}/about", wait_until="domcontentloaded")
        await page.evaluate("""([u, p]) => fetch('/api/method/login', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({usr: u, pwd: p}).toString()})""", [USER, PWD])
        await page.goto(f"http://{site}/re-portal", wait_until="networkidle")
        for sc in screens:
            await page.evaluate(f"showScreen('{sc}')"); await page.wait_for_timeout(1800)
            await page.screenshot(path=f"{out}/console_{sc}_{width}{os.environ.get('SHOT_TAG', '')}.png")
        print("errors:", errs)
        await b.close()
asyncio.run(main())
