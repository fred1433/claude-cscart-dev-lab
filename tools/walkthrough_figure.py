#!/usr/bin/env python3
"""Compose the before / after / restored phone screenshots into one annotated image.

    python3 tools/walkthrough_figure.py <out.png> <img> "<caption>" <img> "<caption>" <img> "<caption>"
"""
import base64
import pathlib
import sys

from playwright.sync_api import sync_playwright


def main(out, items):
    cells = []
    for i in range(0, len(items), 2):
        data = base64.b64encode(pathlib.Path(items[i]).read_bytes()).decode()
        title, _, detail = items[i + 1].partition("|")
        cells.append('<figure><div class="frame"><img src="data:image/png;base64,%s"></div>'
                     '<figcaption><b>%s</b><span>%s</span></figcaption></figure>' % (data, title, detail))
    html = """<!doctype html><html><head><meta charset="utf-8"><style>
    body { margin: 0; background: #ffffff; font: 15px/1.4 -apple-system, Segoe UI, Helvetica, Arial, sans-serif; color: #1d252c; }
    .row { display: flex; gap: 28px; align-items: flex-start; padding: 28px; }
    figure { margin: 0; width: 300px; }
    .frame { height: 600px; overflow: hidden; border: 1px solid #c9ced3; border-radius: 6px; background: #f3f4f6; }
    img { display: block; }
    figcaption { margin-top: 10px; }
    figcaption b { display: block; font-size: 16px; }
    figcaption span { color: #4a5560; font-size: 13.5px; }
    </style></head><body><div class="row">%s</div></body></html>""" % "".join(cells)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1040, "height": 760}, device_scale_factor=2)
        page.set_content(html)
        # same scale for every shot (375 css px -> 300 px), so a page wider than the phone shows cut off
        page.evaluate("() => document.querySelectorAll('img').forEach(i => i.style.width = (i.naturalWidth / 2 * 0.8) + 'px')")
        page.locator(".row").screenshot(path=out)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
