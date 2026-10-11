#!/usr/bin/env python3
"""Screenshot a preview at phone and desktop widths and report horizontal overflow.
Needs Playwright (pip install playwright && playwright install chromium); only
used to produce the walkthrough images, not by the kit.

    python3 tools/screenshot.py <preview.html> <out-prefix>
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright


def main(html, prefix):
    url = pathlib.Path(html).resolve().as_uri()
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, width in (("phone", 375), ("desktop", 1024)):
            page = browser.new_page(viewport={"width": width, "height": 780}, device_scale_factor=2)
            page.goto(url)
            report[name] = page.evaluate(
                "() => ({viewport: window.innerWidth, scrollWidth: document.documentElement.scrollWidth,"
                " formWidth: Math.round(document.querySelector('.ty-catalog-request').getBoundingClientRect().width)})")
            page.screenshot(path="%s-%s.png" % (prefix, name), full_page=True)
            page.close()
        browser.close()
    print(json.dumps(report))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
