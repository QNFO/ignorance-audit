"""Render poster.html to an A0 PDF and a 300 dpi PNG, and report any overflow."""
import sys, asyncio, pathlib
from playwright.async_api import async_playwright

src = pathlib.Path(sys.argv[1]).resolve()
out = src.with_suffix("")
dpi_png = int(sys.argv[2]) if len(sys.argv) > 2 else 60
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        # A0 at 96 css px per inch: 841mm x 1189mm
        w, h = round(841 / 25.4 * 96), round(1189 / 25.4 * 96)
        page = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=dpi_png / 96)
        await page.goto(src.as_uri())
        await page.wait_for_load_state("networkidle")
        await page.evaluate("document.fonts.ready")
        info = await page.evaluate("""() => {
          const main = document.querySelector('main'), foot = document.querySelector('footer');
          const r = main.getBoundingClientRect(), f = foot.getBoundingClientRect();
          let last = 0; main.querySelectorAll(':scope > *').forEach(e => last = Math.max(last, e.getBoundingClientRect().bottom));
          const over = [];
          document.querySelectorAll('section, .phase, .layer, .card, td').forEach(e => { if (e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2) over.push(e.className || e.tagName); });
          const fs = [...document.querySelectorAll('body *')].filter(e => e.childNodes && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
                     .map(e => parseFloat(getComputedStyle(e).fontSize));
          return {mainContentBottom: last, footerTop: f.top, gap: f.top - last, pageH: document.body.scrollHeight, viewH: innerHeight,
                  minFontPx: Math.min(...fs), overflow: over.slice(0, 10)};
        }""")
        print(info, "min font pt:", round(info["minFontPx"] * 0.75, 2))
        await page.screenshot(path=str(out) + ".png", full_page=False)
        await page.pdf(path=str(out) + ".pdf", width="841mm", height="1189mm", print_background=True, prefer_css_page_size=True)
        await b.close()

asyncio.run(main())
