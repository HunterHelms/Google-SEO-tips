# Google Search Central in Markdown

This project is a Markdown version of [Google Search Central](https://developers.google.com/search),
organized so it is easy to search, read, and use as context for AI agents.

The source material comes from Google's public Search documentation, primarily
[developers.google.com/search/docs](https://developers.google.com/search/docs). The repo keeps each
page as a plain `.md` file with headings, links, code samples, tables, notes, and images preserved
where practical.

## Why This Exists

Google Search Central is useful, but web pages are not always the best format for local search,
retrieval, agent context windows, or lightweight documentation workflows.

This repo turns that documentation into a simple file tree that can be:

- searched with tools like `rg`, `grep`, or your editor
- indexed by local RAG systems or AI coding agents
- read without browser navigation or page chrome
- refreshed from the live Google docs when needed

## Contents

The repository currently contains 154 Markdown documentation pages.

Top-level sections include:

- `seo-fundamentals/`
- `crawling-and-indexing/`
- `appearance/`
- `appearance/structured-data/`
- `monitor-debug/`
- `specialty/`
- `guides/`

The naming mostly follows Google Search documentation paths, with a few existing repo-friendly
aliases preserved, such as `seo-fundamentals` and `crawling-and-indexing`.

## Searching

Search the full collection:

```bash
rg "canonical"
```

Search within one section:

```bash
rg "robots.txt" crawling-and-indexing
```

Find pages by title:

```bash
rg "^# " .
```

Find structured data guidance:

```bash
rg "required properties" appearance/structured-data
```

## Refreshing the Docs

This repo includes a small fetcher that discovers the current Google Search docs tree and converts
pages to Markdown.

Fetch only missing or empty files:

```bash
python3 scripts/fetch_google_search_docs.py
```

Refresh every page from the live docs:

```bash
python3 scripts/fetch_google_search_docs.py --overwrite
```

Refresh one page:

```bash
python3 scripts/fetch_google_search_docs.py --overwrite --only /search/docs
```

## Notes for AI Agents

Use this repository as a local knowledge base for Search Central guidance. Prefer exact citations to
the Markdown file path you used, and when recommendations may have changed, refresh the docs before
answering.

Good entry points:

- `docs.md` for the documentation landing page
- `overview.md`, `technical-requirements.md`, and `spam-policies.md` for Search Essentials
- `seo-fundamentals/seo-starter-guide.md` for broad SEO basics
- `crawling-and-indexing/overview.md` for crawling and indexing behavior
- `appearance/structured-data/search-gallery.md` for rich result features

## Attribution and License

The source content is from Google Search Central on Google for Developers.

Google's page footer states that, unless otherwise noted, page content is licensed under the
[Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/) and code
samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
See the [Google Developers Site Policies](https://developers.google.com/site-policies) for details.
