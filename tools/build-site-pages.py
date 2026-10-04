#!/usr/bin/env python3
"""Stage the website and only its referenced media for GitHub Pages."""

from html.parser import HTMLParser
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "_site"


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.urls.append(value)


def main() -> None:
    DEST.mkdir(exist_ok=True)
    for directory in ("site", "docs"):
        for source in (ROOT / directory).rglob("*"):
            if source.is_file():
                target = DEST / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                # Pages artifacts cannot contain symlinks. Copy their contents.
                shutil.copyfile(source, target)
    shutil.copyfile(ROOT / "LICENSE", DEST / "LICENSE")
    for page in (ROOT / "site").glob("*.html"):
        parser = References()
        parser.feed(page.read_text())
        for url in parser.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            source = (page.parent / unquote(parts.path)).resolve()
            relative = source.relative_to(ROOT)
            if relative.parts[0] != "media":
                continue
            if not source.is_file():
                raise FileNotFoundError(f"{page.name} references missing media: {url}")
            target = DEST / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    (DEST / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0;url=site/index.html">'
        '<title>ArCHi</title></head><body>'
        '<a href="site/index.html">Explore ArCHi and watch the presentations</a>'
        '</body></html>\n'
    )
    (DEST / ".nojekyll").touch()
    print(f"Prepared GitHub Pages website at {DEST}")


if __name__ == "__main__":
    main()
