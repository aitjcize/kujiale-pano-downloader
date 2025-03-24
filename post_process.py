#!/usr/bin/env python3

import os
import re
import requests
import subprocess
from pathlib import Path
from urllib.parse import urlparse, unquote, urlencode

# Base directory for all downloaded files
BASE_DIR = Path('./webroot')
MAIN_DOMAIN = 'www.kujiale.com'
EXCLUDE_REWRITE = [
    MAIN_DOMAIN,
    'qhstaticssl.kujiale.com',
]

DIRECTIONAL_SUFFIXES = ['f', 'b', 'l', 'r', 'u', 'd']
HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

# Match any *.kujiale.com domain except www.kujiale.com with both https:// and protocol-relative //
URL_PATTERN = re.compile(r'((?:https:|)\/\/([^\/]+\.kujiale\.com)\/[^\s"\'\)\]]+)')


def is_text_file(path: Path) -> bool:
    """Check if a file is a text file based on mime type."""
    try:
        output = subprocess.check_output(
            ['file', '--mime-type', str(path)], stderr=subprocess.DEVNULL
        )
        mime = output.decode().strip().split(': ')[-1]
        return mime.startswith('text') or mime == 'application/json'
    except Exception:
        return False


def get_download_path(domain):
    """Get the download path for a given domain."""
    return BASE_DIR / domain


def download_file(url: str, local_path: Path):
    """Download a file from URL to local_path."""
    if local_path.exists():
        return

    parsed = urlparse(url)
    if parsed.path.startswith('/download'):
        return

    try:
        print(f"[DOWNLOADING] {url}")
        os.makedirs(local_path.parent, exist_ok=True)
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(resp.content)
    except Exception as e:
        print(f"[FAILED] {url} -> {e}")


def normalize_path(parsed_url):
    """Construct a path including query string as a filename."""
    domain = parsed_url.netloc
    path = unquote(parsed_url.path).lstrip("/")
    if parsed_url.query:
        path += "__" + parsed_url.query.replace("/", "_").replace(":", "_").replace("?", "_")
    return get_download_path(domain) / path


def should_process_domain(domain):
    """Check if this domain should be processed."""
    return (
        domain.endswith('.kujiale.com') and domain != 'panojson-oss.kujiale.com'
        and domain != MAIN_DOMAIN
    )


def handle_url(url: str):
    """Process a URL for downloading."""
    if url.startswith('//'):
        url = 'https:' + url

    parsed = urlparse(url)
    if not should_process_domain(parsed.netloc):
        return

    local_path = normalize_path(parsed)
    download_file(url, local_path)


def download_all_urls(urls):
    """Process all URLs in the set, expanding templates with directional suffixes."""
    for url in urls:
        if '%s' in url:
            for suffix in DIRECTIONAL_SUFFIXES:
                expanded_url = url.replace('%s', suffix)
                handle_url(expanded_url)

                info_url = expanded_url.split('?')[0] + '?x-oss-process=image/info'
                handle_url(info_url)

                resize_url = expanded_url.split('?')[
                    0
                ] + '?x-oss-process=image/resize,w_256|image/quality,q_100|image/format,webp/quality,q_100'
                handle_url(resize_url)

                for y in [0, 1, 2]:
                    for x in [0, 1, 2]:
                        resize_url = expanded_url.split('?')[
                            0
                        ] + f'?x-oss-process=image/indexcrop,x_512,i_{x}|image/indexcrop,y_512,i_{y}|image/quality,q_100|image/format,webp/quality,q_100'
                        handle_url(resize_url)
                        resize_url = expanded_url.split('?')[
                            0
                        ] + f'?x-oss-process=image/resize,w_512|image/indexcrop,x_512,i_{x}|image/indexcrop,y_512,i_{y}|image/quality,q_100|image/format,webp/quality,q_100'
                        handle_url(resize_url)
                        resize_url = expanded_url.split('?')[
                            0
                        ] + f'?x-oss-process=image/resize,w_1024|image/indexcrop,x_512,i_{x}|image/indexcrop,y_512,i_{y}|image/quality,q_100|image/format,webp/quality,q_100'
                        handle_url(resize_url)
        else:
            handle_url(url)


def extract_and_rewrite_file(urls: set, file_path: Path):
    """Find kujiale.com URLs in a file, add to download queue, and rewrite to relative paths."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"Skipping {file_path}: {e}")
        return

    matches = URL_PATTERN.findall(content)
    if not matches:
        return

    for match in matches:
        url = match[0]
        domain = match[1]

        # Only download render data.
        if domain != 'qhrenderpicoss.kujiale.com':
            continue

        # Ensure URL has protocol for downloading
        if url.startswith('//'):
            url = 'https:' + url
        urls.add(url)

        domain_dir = get_download_path(domain)
        os.makedirs(domain_dir, exist_ok=True)

    # Rewrite URLs to be relative to our server
    modified = content

    https_pattern = r'https://([^/]+\.kujiale\.com/[^\s"\'\)\]]+)'
    https_matches = re.findall(https_pattern, content)
    for domain_path in https_matches:
        domain = domain_path.split('/')[0]
        if domain not in EXCLUDE_REWRITE:
            modified = modified.replace(f'https://{domain_path}', f'/{domain_path}')

    protocol_pattern = r'//([^/]+\.kujiale\.com/[^\s"\'\)\]]+)'
    protocol_matches = re.findall(protocol_pattern, modified)
    for domain_path in protocol_matches:
        domain = domain_path.split('/')[0]
        if domain not in EXCLUDE_REWRITE:
            modified = modified.replace(f'//{domain_path}', f'/{domain_path}')

    try:
        file_path.write_text(modified, encoding='utf-8')
        print(f"[UPDATED] {file_path.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"[ERROR] Writing {file_path}: {e}")


def add_redirect_to_airoaming():
    # Create a index.html in BASE_DIR which redirects to /cloud/design/<id>/airoaming/
    # We need to find the design id first by looking at our local directory under BASE_DIR/cloud/design.
    for file_path in BASE_DIR.rglob("cloud/design/*/airoaming/index.html"):
        if file_path.is_file() and file_path.name == "index.html":
            design_id = file_path.parent.parent.name
            break

    # Redirect to /cloud/design/<id>/airoaming/
    redirect_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=/cloud/design/{design_id}/airoaming/">
</head>
<body>
    Redirecting to <a href="/cloud/design/{design_id}/airoaming/">/cloud/design/{design_id}/airoaming/</a>
</body>
</html>
"""
    (BASE_DIR / "index.html").write_text(redirect_html, encoding='utf-8')


def main():
    """Main function to process all text files in BASE_DIR and download found URLs."""
    urls = set()
    for file_path in BASE_DIR.rglob("*"):
        if file_path.is_file() and is_text_file(file_path):
            extract_and_rewrite_file(urls, file_path)

    add_redirect_to_airoaming()
    download_all_urls(urls)


if __name__ == "__main__":
    main()
