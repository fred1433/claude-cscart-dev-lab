#!/usr/bin/env python3
"""Render the catalog request form (.tpl + .less) to a static HTML preview.

The fixture's Smarty template uses only a tiny subset of tags, so this does not
need PHP or Smarty: {** comments **}, {__("key")} labels, {""|fn_url} and
{hook}...{/hook}. Any other tag stops the render, so a template change that
needs real Smarty is noticed rather than faked.

    python3 tools/render_preview.py <dev-copy-folder> <out.html>
"""
import os
import re
import sys

LABELS = {
    "catalog_request.title": "Request a printed catalog",
    "catalog_request.intro": "Tell us where to send it. We mail catalogs within two business days.",
    "catalog_request.name": "Full name",
    "catalog_request.company": "Company",
    "catalog_request.email": "Email",
    "catalog_request.address": "Mailing address",
    "catalog_request.zip": "ZIP code",
    "catalog_request.interests": "What would you like?",
    "catalog_request.printed_catalog": "Printed catalog",
    "catalog_request.seasonal_flyer": "Seasonal flyer",
    "catalog_request.sample_pack": "Sample pack",
    "catalog_request.send": "Send my request",
}
THEME = "design/themes/custom_theme"
TPL = THEME + "/templates/addons/catalog_request/blocks/catalog_request_form.tpl"
CSS = [THEME + "/css/tygh/forms.less", THEME + "/css/addons/catalog_request/styles.less"]


def render(root):
    with open(os.path.join(root, TPL)) as handle:
        tpl = handle.read()
    tpl = re.sub(r"\{\*\*.*?\*\*\}", "", tpl, flags=re.S)
    tpl = re.sub(r'\{__\("([^"]+)"\)\}', lambda m: LABELS.get(m.group(1), m.group(1)), tpl)
    tpl = tpl.replace('{""|fn_url}', "#")
    tpl = re.sub(r'\{hook name="[^"]+"\}|\{/hook\}', "", tpl)
    leftover = re.findall(r"\{[^}\s][^}]*\}", tpl)
    if leftover:
        raise SystemExit("unsupported Smarty tags: %s" % leftover)
    css = "\n".join(open(os.path.join(root, path)).read() for path in CSS)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catalog request form preview</title>
<style>
body { margin: 0; font: 14px/1.45 Arial, Helvetica, sans-serif; color: #24303b; background: #f3f4f6; }
.lab-header { padding: 14px 16px; background: #24303b; color: #fff; font-weight: 600; }
</style>
<style>%s</style>
</head><body><div class="lab-header">Store header (preview)</div>%s</body></html>
""" % (css, tpl)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    with open(sys.argv[2], "w") as handle:
        handle.write(render(sys.argv[1]))
