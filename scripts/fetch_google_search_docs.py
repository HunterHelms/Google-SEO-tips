#!/usr/bin/env python3
"""Fetch Google Search Central docs pages into local Markdown files."""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


BASE_URL = "https://developers.google.com"
DOCS_ROOT = "/search/docs"
START_URL = f"{BASE_URL}{DOCS_ROOT}"


EXISTING_PATH_ALIASES = {
    "/search/docs": "docs.md",
    "/search/docs/essentials": "overview.md",
    "/search/docs/essentials/technical": "technical-requirements.md",
    "/search/docs/essentials/spam-policies": "spam-policies.md",
    "/search/docs/fundamentals/seo-starter-guide": "seo-fundamentals/seo-starter-guide.md",
    "/search/docs/fundamentals/how-search-works": "seo-fundamentals/how-google-search-works.md",
    "/search/docs/fundamentals/creating-helpful-content": (
        "seo-fundamentals/creating-helpful-reliable-people-first-content.md"
    ),
    "/search/docs/fundamentals/ai-optimization-guide": (
        "seo-fundamentals/optimizing-for-generative-ai.md"
    ),
    "/search/docs/fundamentals/using-gen-ai-content": (
        "seo-fundamentals/guidance-on-using-generative-ai.md"
    ),
    "/search/docs/fundamentals/get-started": "seo-fundamentals/maintaining-your-sites-SEO.md",
    "/search/docs/fundamentals/get-started-developers": "seo-fundamentals/devs-guide-to-search.md",
    "/search/docs/fundamentals/do-i-need-seo": "seo-fundamentals/do-you-need-an-SEO.md",
    "/search/docs/fundamentals/third-party-seo": "seo-fundamentals/guidance-on-3rd-party-tools.md",
    "/search/docs/crawling-indexing": "crawling-and-indexing/overview.md",
    "/search/docs/crawling-indexing/indexable-file-types": (
        "crawling-and-indexing/file-types-indexable-by-google.md"
    ),
    "/search/docs/crawling-indexing/url-structure": "crawling-and-indexing/url-structure.md",
    "/search/docs/crawling-indexing/links-crawlable": "crawling-and-indexing/links.md",
    "/search/docs/crawling-indexing/sitemaps/overview": (
        "crawling-and-indexing/sitemaps/learn-about-sitemaps.md"
    ),
    "/search/docs/crawling-indexing/sitemaps/build-sitemap": (
        "crawling-and-indexing/sitemaps/build-and-submit-sitemaps.md"
    ),
    "/search/docs/crawling-indexing/sitemaps/large-sitemaps": (
        "crawling-and-indexing/sitemaps/sitemap-index-file.md"
    ),
    "/search/docs/crawling-indexing/sitemaps/image-sitemaps": (
        "crawling-and-indexing/sitemaps/sitemap extensions/image-sitemaps.md"
    ),
}


SKIP_SELECTORS = [
    "script",
    "style",
    "noscript",
    "devsite-toc",
    "devsite-feedback",
    "devsite-page-rating",
    "devsite-bookmark",
    "devsite-selector",
    ".devsite-article-meta",
    ".devsite-page-rating",
    ".devsite-feedback",
    ".devsite-banner",
    ".devsite-landing-row-cards",
]


SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (compatible; GoogleSearchDocsMarkdownFetcher/1.0; "
            "+https://developers.google.com/search/docs)"
        )
    }
)


MATERIAL_ICON_LABELS = {
    "build_circle",
    "code",
    "find_in_page",
    "help",
    "home",
    "looks_one",
    "looks_two",
    "menu_book",
    "pageview",
    "school",
    "video_library",
}


def normalize_space(text: str) -> str:
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_title(raw_title: str) -> str:
    title = normalize_space(raw_title)
    title = re.sub(r"\s*\|\s*Documentation\s*\|\s*Google for Developers\s*$", "", title)
    title = re.sub(r"\s*\|\s*Google for Developers\s*$", "", title)
    return title


def canonical_path(url: str) -> str | None:
    full_url, _fragment = urldefrag(urljoin(BASE_URL, url))
    parsed = urlparse(full_url)
    if parsed.netloc != "developers.google.com":
        return None
    path = parsed.path.rstrip("/") or "/"
    if path == DOCS_ROOT or path.startswith(f"{DOCS_ROOT}/"):
        return path
    return None


def discover_doc_paths() -> list[str]:
    response = SESSION.get(START_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    paths: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        path = canonical_path(anchor["href"])
        if not path or path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def path_to_markdown(path: str) -> Path:
    if path in EXISTING_PATH_ALIASES:
        return Path(EXISTING_PATH_ALIASES[path])

    rel = path.removeprefix(f"{DOCS_ROOT}/")
    parts = rel.split("/")
    if parts[0] == "fundamentals":
        parts[0] = "seo-fundamentals"
    elif parts[0] == "crawling-indexing":
        parts[0] = "crawling-and-indexing"

    return Path(*parts).with_suffix(".md")


def fetch_soup(path: str) -> BeautifulSoup:
    response = SESSION.get(f"{BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def remove_site_chrome(root: Tag) -> None:
    for selector in SKIP_SELECTORS:
        for node in root.select(selector):
            node.decompose()
    for node in root.select("[hidden], .devsite-hidden, .hidden"):
        node.decompose()
    for heading in root.find_all(string=re.compile(r"Spot something weird\?", re.I)):
        parent = heading.parent
        while isinstance(parent, Tag) and parent is not root:
            if parent.name in {"section", "div"}:
                parent.decompose()
                break
            parent = parent.parent


def inline_text(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return normalize_space(str(node))
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name in {"script", "style", "noscript"}:
        return ""
    if name == "br":
        return "\n"
    if name == "code":
        return f"`{normalize_space(node.get_text(' ', strip=True))}`"
    if name in {"strong", "b"}:
        text = join_inline(node.children)
        return f"**{text}**" if text else ""
    if name in {"em", "i"}:
        text = join_inline(node.children)
        return f"*{text}*" if text else ""
    if name == "a":
        text = join_inline(node.children) or normalize_space(node.get_text(" ", strip=True))
        href = node.get("href", "")
        if text in MATERIAL_ICON_LABELS:
            return ""
        if not href or href.startswith("#"):
            return text
        url = urljoin(BASE_URL, href)
        if " " in text:
            maybe_icon, rest = text.split(" ", 1)
            if maybe_icon in MATERIAL_ICON_LABELS:
                text = rest.strip()
        return f"[{text}]({url})" if text else url
    if name == "img":
        alt = normalize_space(node.get("alt", ""))
        src = node.get("src") or node.get("data-src") or ""
        return f"![{alt}]({urljoin(BASE_URL, src)})" if src else alt
    classes = " ".join(node.get("class", []))
    if name in {"devsite-icon", "span"} and "material" in classes:
        return ""
    return join_inline(node.children)


def join_inline(children: Iterable[Tag | NavigableString]) -> str:
    pieces = [inline_text(child) for child in children]
    text = " ".join(piece for piece in pieces if piece)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([(\[])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]])", r"\1", text)
    return normalize_space(text)


def table_to_markdown(table: Tag) -> str:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        rows.append([normalize_space(cell.get_text(" ", strip=True)).replace("|", "\\|") for cell in cells])
    if not rows:
        return ""

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    separator = ["---"] * width
    body = rows[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def list_to_markdown(list_node: Tag, indent: int = 0) -> str:
    ordered = list_node.name.lower() == "ol"
    lines: list[str] = []
    index = 1
    for li in list_node.find_all("li", recursive=False):
        child_blocks = []
        inline_parts = []
        for child in li.children:
            if isinstance(child, Tag) and child.name in {"ul", "ol", "pre", "table", "aside"}:
                child_blocks.append(markdown_for_node(child, indent + 2))
            else:
                inline_parts.append(inline_text(child))

        marker = f"{index}." if ordered else "-"
        prefix = " " * indent + marker + " "
        text = normalize_space(" ".join(part for part in inline_parts if part))
        if text:
            lines.append(prefix + text)
        for block in child_blocks:
            if block:
                lines.append(block)
        index += 1
    return "\n".join(lines)


def aside_to_markdown(aside: Tag) -> str:
    classes = " ".join(aside.get("class", [])).lower()
    if "warning" in classes:
        label = "WARNING"
    elif "caution" in classes:
        label = "CAUTION"
    elif "key-point" in classes or "important" in classes:
        label = "IMPORTANT"
    else:
        label = "NOTE"

    content = blocks_to_markdown(aside.children)
    quoted = [f"> {line}" if line else ">" for line in content.splitlines()]
    return f"> [!{label}]\n" + "\n".join(quoted)


def markdown_for_node(node: Tag | NavigableString, indent: int = 0) -> str:
    if isinstance(node, NavigableString):
        return normalize_space(str(node))
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name in {"script", "style", "noscript"}:
        return ""
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(name[1])
        return "#" * level + " " + join_inline(node.children)
    if name == "p":
        return join_inline(node.children)
    if name == "pre":
        code = node.get_text("\n").strip("\n")
        return f"```\n{code}\n```"
    if name in {"ul", "ol"}:
        return list_to_markdown(node, indent)
    if name == "table":
        return table_to_markdown(node)
    if name == "aside":
        return aside_to_markdown(node)
    if name == "blockquote":
        content = blocks_to_markdown(node.children)
        return "\n".join(f"> {line}" if line else ">" for line in content.splitlines())
    if name == "img":
        return inline_text(node)
    if name in {"figure", "picture"}:
        return blocks_to_markdown(node.children)
    if name in {"devsite-code", "devsite-selector"}:
        return blocks_to_markdown(node.children)
    if name in {"section", "article", "div", "main", "td", "th", "details"}:
        return blocks_to_markdown(node.children)
    if name == "summary":
        return f"**{join_inline(node.children)}**"
    return inline_text(node)


def blocks_to_markdown(children: Iterable[Tag | NavigableString]) -> str:
    blocks: list[str] = []
    for child in children:
        text = markdown_for_node(child)
        if text:
            blocks.append(text)
    return "\n\n".join(blocks)


def page_to_markdown(soup: BeautifulSoup) -> str:
    title = clean_title(soup.title.get_text(" ", strip=True) if soup.title else "")
    root = soup.select_one(".devsite-article-body") or soup.select_one("article") or soup.select_one("main")
    if root is None:
        raise ValueError("Could not find article content")

    remove_site_chrome(root)
    body = blocks_to_markdown(root.children)
    markdown = f"# {title}\n\n{body}\n" if title else f"{body}\n"
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip() + "\n"


def should_write(path: Path, overwrite: bool) -> bool:
    if overwrite:
        return True
    if not path.exists():
        return True
    return not path.read_text(encoding="utf-8").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="Rewrite existing non-empty Markdown files.")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between page fetches.")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Fetch only this docs path or URL. Can be passed more than once.",
    )
    args = parser.parse_args()

    paths = [canonical_path(path) for path in args.only] if args.only else discover_doc_paths()
    paths = [path for path in paths if path]
    written = 0
    skipped = 0
    failures: list[tuple[str, str]] = []

    print(f"Discovered {len(paths)} Google Search docs pages.")
    for index, doc_path in enumerate(paths, start=1):
        out_path = path_to_markdown(doc_path)
        if not should_write(out_path, args.overwrite):
            skipped += 1
            print(f"[{index:03}/{len(paths)}] skip  {out_path}")
            continue

        try:
            soup = fetch_soup(doc_path)
            markdown = page_to_markdown(soup)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(markdown, encoding="utf-8")
            written += 1
            print(f"[{index:03}/{len(paths)}] write {out_path}")
            time.sleep(args.delay)
        except Exception as exc:  # noqa: BLE001
            failures.append((doc_path, str(exc)))
            print(f"[{index:03}/{len(paths)}] fail  {doc_path}: {exc}", file=sys.stderr)

    print(f"Done. Wrote {written}, skipped {skipped}, failed {len(failures)}.")
    if failures:
        for doc_path, error in failures:
            print(f"- {doc_path}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
