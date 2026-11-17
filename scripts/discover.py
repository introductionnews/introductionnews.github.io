
import html
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://hrblockknowledgefrequent.zohodesk.com"
KB_URL = BASE_URL + "/portal/en/kb/hrblockknowledgefrequent"
KB_PATH = "/portal/en/kb/hrblockknowledgefrequent"

GITHUB_URL = "https://introductionnews.github.io/"
MAX_PAGES = 100

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KnowledgeDiscoveryBot/1.0)"
}

session = requests.Session()
session.headers.update(HEADERS)


def clean_url(url):
    parsed = urlparse(url)

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        "",
        "",
        ""
    ))


def get_page(url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def load_existing_articles():
    articles = {}

    try:
        with open("index.html", "r", encoding="utf-8") as file:
            source = file.read()

        soup = BeautifulSoup(source, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = urljoin(GITHUB_URL, anchor["href"])
            parsed = urlparse(href)

            if parsed.netloc.lower() != urlparse(BASE_URL).netloc.lower():
                continue

            if "/portal/en/kb/articles/" not in parsed.path:
                continue

            article_url = clean_url(href)
            title = anchor.get_text(" ", strip=True)

            if not title:
                title = parsed.path.rstrip("/").split("/")[-1]
                title = re.sub(r"[-_]+", " ", title)

            articles[article_url] = title

    except FileNotFoundError:
        print("No existing homepage found. Starting fresh.")

    print("Existing articles preserved:", len(articles))
    return articles


def discover_articles(articles):
    pending = [KB_URL]
    visited = set()

    while pending and len(visited) < MAX_PAGES:
        current = pending.pop(0)

        if current in visited:
            continue

        visited.add(current)
        print("Checking:", current)

        try:
            source = get_page(current)
        except requests.RequestException as error:
            print("Unable to open page:", error)
            continue

        soup = BeautifulSoup(source, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = urljoin(current, anchor["href"])
            parsed = urlparse(href)

            if parsed.netloc.lower() != urlparse(BASE_URL).netloc.lower():
                continue

            path = parsed.path

            if "/portal/en/kb/articles/" in path:
                article_url = clean_url(href)

                title = anchor.get_text(" ", strip=True)

                if not title:
                    title = anchor.get("title", "")

                if not title:
                    title = path.rstrip("/").split("/")[-1]
                    title = re.sub(r"[-_]+", " ", title)

                articles[article_url] = title

            elif path == KB_PATH or path.startswith(KB_PATH + "/"):
                next_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    ""
                ))

                if next_url not in visited and next_url not in pending:
                    pending.append(next_url)

        time.sleep(0.5)

    return articles


def build_homepage(articles):
    cards = []

    sorted_articles = sorted(
        articles.items(),
        key=lambda item: item[1].lower()
    )

    for number, (url, title) in enumerate(sorted_articles, start=1):
        cards.append(f"""
        <a class="article-card"
           href="{html.escape(url, quote=True)}"
           target="_blank"
           rel="noopener noreferrer">
            <span class="number">{number:02d}</span>
            <span class="article-title">{html.escape(title)}</span>
            <span class="arrow">↗</span>
        </a>
        """)

    article_html = "\n".join(cards)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="msvalidate.01" content="0C930A4ADBB0E8FA189A9C17547982BF" />
<title>H&R Block Knowledge Base - All Articles | Introduction News</title>

<meta name="description"
content="Browse H&R Block software information, installation guides,
download instructions, activation information and knowledge base articles.">

<meta name="robots" content="index, follow">

<link rel="canonical" href="{GITHUB_URL}">
<link rel="stylesheet" href="style.css">
</head>

<body>

<header class="site-header">
    <div class="container">
        <div class="brand">Introduction News</div>
        <p>Software Information and Knowledge Resources</p>
    </div>
</header>

<main class="container">

<section class="intro">
    <span class="eyebrow">Knowledge Resource Directory</span>

    <h1>H&R Block Software Help and Guides</h1>

    <p>
        Browse the available H&R Block knowledge base article links.
        Find information about software downloads, installation,
        activation, existing purchases and general product guidance.
        Each article opens on its original Zoho Knowledge Base page.
    </p>

    <a class="main-link"
       href="{KB_URL}"
       target="_blank"
       rel="noopener noreferrer">
       Visit Original Knowledge Base
    </a>
</section>

<section class="articles">

    <div class="section-heading">
        <div>
            <span class="eyebrow">Article Collection</span>
            <h2>All Available Knowledge Base Articles</h2>
        </div>

        <span class="count">{len(sorted_articles)} Articles</span>
    </div>

    <div class="article-list">
        {article_html}
    </div>

</section>

<section class="notice">
    <h2>About This Directory</h2>

    <p>
        This website provides an independent directory of links
        to articles hosted on the original Zoho Knowledge Base.
    </p>

    <p>
        Article content remains hosted on its original website.
        This directory is not affiliated with or endorsed by
        H&R Block or Zoho.
    </p>
</section>

</main>

<footer>
    <div class="container">
        Introduction News - Independent Knowledge Directory
    </div>
</footer>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as file:
        file.write(page)


def build_sitemap():
    today = datetime.now(timezone.utc).date().isoformat()

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{GITHUB_URL}</loc>
        <lastmod>{today}</lastmod>
    </url>
</urlset>
"""

    with open("sitemap.xml", "w", encoding="utf-8") as file:
        file.write(sitemap)


def build_robots():
    robots = f"""User-agent: *
Allow: /

Sitemap: {GITHUB_URL}sitemap.xml
"""

    with open("robots.txt", "w", encoding="utf-8") as file:
        file.write(robots)


def main():
    articles = load_existing_articles()

    articles = discover_articles(articles)

    if not articles:
        raise RuntimeError(
            "No article links are available. Existing files were not updated."
        )

    print("Total articles available:", len(articles))

    build_homepage(articles)
    build_sitemap()
    build_robots()

    print("Homepage updated.")
    print("Sitemap updated.")
    print("Robots.txt updated.")
    print("Discovery completed.")


if __name__ == "__main__":
    main()
