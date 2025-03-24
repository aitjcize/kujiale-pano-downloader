from mitmproxy import http
import os
import re
import urllib.parse

DUMP_DIR = "./webroot"
MAIN_DOMAIN = 'www.kujiale.com'


def should_process_domain(domain):
    """Check if this domain should be processed."""
    return domain.endswith('.kujiale.com') and domain != MAIN_DOMAIN


def sanitize_path(url):
    parsed = urllib.parse.urlparse(url)
    path = parsed.path

    # For kujiale.com subdomains
    if not path or path.endswith("/"):
        path += "index.html"

    # For subdomains, ensure domain is part of the directory structure
    domain_dir = parsed.netloc
    if domain_dir != MAIN_DOMAIN:
        path = os.path.join(domain_dir, path.lstrip('/'))

    # Add query parameters to filename for CDN-like content
    if (
        parsed.query and 'kujiale.com' in parsed.netloc
        and parsed.netloc != 'panojson-oss.kujiale.com' and parsed.netloc != MAIN_DOMAIN
    ):
        query_suffix = "__" + parsed.query.replace("/", "_").replace(":", "_").replace("?", "_")
        path += query_suffix

    return os.path.join(DUMP_DIR, *path.strip("/").split("/"))


def response(flow: http.HTTPFlow):
    url = flow.request.pretty_url
    domain = urllib.parse.urlparse(url).netloc

    content = flow.response.content
    if not content:
        return

    file_path = sanitize_path(url)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    content_type = flow.response.headers.get("content-type", "").split(";")[0].strip()

    try:
        if content_type.startswith("text/") or content_type in (
            "application/json", "application/javascript"
        ):
            text = content.decode('utf-8', errors='replace')
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(text)
            print(f"[TEXT] Saved: {file_path}")
        else:
            with open(file_path, "wb") as f:
                f.write(content)
            print(f"[BINARY] Saved: {file_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save {url} -> {e}")
