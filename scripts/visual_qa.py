"""Screenshot sweep for visual QA against a running Datasette.

Usage: uv run python scripts/visual_qa.py [--base-url http://localhost:8001]
Outputs PNGs to tmp/qa/<browser>/<viewport>/ and a contact sheet at tmp/qa/index.html.
"""
from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

ROUTES: list[tuple[str, str]] = [
    ("home", "/"),
    ("about", "/about"),
    ("how-to-use", "/how-to-use"),
    ("sources", "/sources"),
    ("status", "/status"),
    ("developers", "/developers"),
    ("search-all", "/-/search"),
    ("database", "/fixtures"),
    ("table-facetable", "/fixtures/facetable"),
    ("table-searchable-fts", "/fixtures/searchable?_search=dog"),
    ("table-sortable", "/fixtures/sortable"),
    ("table-roadside", "/fixtures/roadside_attractions"),
    ("row-view", "/fixtures/roadside_attractions/1"),
    ("query-sql", "/fixtures?sql=select+pk%2C+state%2C+on_earth+from+facetable+limit+10"),
]

VIEWPORTS: dict[str, dict[str, int]] = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}

BROWSERS = ("chromium", "webkit")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


async def shoot(base_url: str, out_root: Path) -> list[dict]:
    results: list[dict] = []
    async with async_playwright() as p:
        for browser_name in BROWSERS:
            browser_type = getattr(p, browser_name)
            browser = await browser_type.launch()
            for vp_name, vp in VIEWPORTS.items():
                context = await browser.new_context(viewport=vp, device_scale_factor=2)
                page = await context.new_page()
                out_dir = out_root / browser_name / vp_name
                out_dir.mkdir(parents=True, exist_ok=True)
                for name, path in ROUTES:
                    url = base_url.rstrip("/") + path
                    file = out_dir / f"{slug(name)}.png"
                    status: int | None = None
                    error: str | None = None
                    try:
                        resp = await page.goto(url, wait_until="networkidle", timeout=15000)
                        status = resp.status if resp else None
                        await page.wait_for_timeout(400)
                        await page.screenshot(path=str(file), full_page=True)
                    except Exception as e:
                        error = str(e)
                    results.append(
                        {
                            "browser": browser_name,
                            "viewport": vp_name,
                            "route": name,
                            "path": path,
                            "status": status,
                            "error": error,
                            "file": file.relative_to(out_root).as_posix(),
                        }
                    )
                    print(f"[{browser_name}/{vp_name}] {path} -> {status} {'ERR: ' + error if error else ''}")
                await context.close()
            await browser.close()
    return results


def write_contact_sheet(results: list[dict], out_root: Path, base_url: str) -> Path:
    by_route: dict[str, list[dict]] = {}
    for r in results:
        by_route.setdefault(r["route"], []).append(r)

    rows: list[str] = []
    for route, items in by_route.items():
        path = items[0]["path"]
        cells: list[str] = []
        for item in sorted(items, key=lambda x: (x["browser"], x["viewport"])):
            label = f"{item['browser']} / {item['viewport']}"
            status_tag = f"<span class='status s{item['status']}'>{item['status'] or 'ERR'}</span>"
            if item["error"]:
                body = f"<div class='err'>{item['error']}</div>"
            else:
                body = f"<a href='{item['file']}' target='_blank'><img src='{item['file']}' loading='lazy'></a>"
            cells.append(f"<figure><figcaption>{label} {status_tag}</figcaption>{body}</figure>")
        rows.append(
            f"<section><h2>{route} <code>{path}</code></h2><div class='grid'>{''.join(cells)}</div></section>"
        )

    html = f"""<!doctype html>
<meta charset='utf-8'>
<title>Zeeker visual QA — {base_url}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 2rem; background: #f8f7f4; color: #1a1a1a; }}
  h1 {{ margin-bottom: .25rem; }}
  .meta {{ color: #666; margin-bottom: 2rem; }}
  section {{ margin-bottom: 3rem; }}
  h2 {{ border-bottom: 1px solid #ddd; padding-bottom: .25rem; }}
  h2 code {{ font-size: .85rem; color: #666; font-weight: normal; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1rem; }}
  figure {{ margin: 0; background: #fff; border: 1px solid #e5e3de; border-radius: 6px; overflow: hidden; }}
  figcaption {{ padding: .5rem .75rem; font-size: .8rem; background: #efece6; display: flex; justify-content: space-between; align-items: center; }}
  img {{ width: 100%; display: block; }}
  .status {{ font-family: ui-monospace, monospace; font-size: .7rem; padding: 2px 6px; border-radius: 3px; background: #ddd; }}
  .s200 {{ background: #cfe8d4; color: #1b5e20; }}
  .s404, .s500 {{ background: #f5c6cb; color: #611a1a; }}
  .err {{ padding: 1rem; color: #a11; font-size: .8rem; font-family: ui-monospace, monospace; }}
</style>
<h1>Zeeker visual QA</h1>
<div class='meta'>Base URL: <code>{base_url}</code> &middot; {len(results)} screenshots</div>
{''.join(rows)}
"""
    out = out_root / "index.html"
    out.write_text(html)
    return out


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--out", default="tmp/qa")
    args = parser.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    results = await shoot(args.base_url, out_root)
    sheet = write_contact_sheet(results, out_root, args.base_url)
    print(f"\nContact sheet: {sheet.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
