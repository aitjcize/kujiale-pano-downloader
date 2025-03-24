# Kujiale (酷家樂) Panorama Downloader

Tools for mirroring and serving Kujiale website content locally.

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Install golang toolchains.

## Usage

This toolkit consists of three main components:

1. **save_responses.py**: A mitmproxy script that captures HTTP responses from kujiale.com domains
2. **post_process.py**: A script that processes saved files to rewrite URLs and download additional resources
3. **serve.go**: A local HTTP server that serves the mirrored content

### Capturing Website Content

To capture website content using mitmproxy:

```bash
mitmdump -s save_responses.py
```

Configure your browser to use the mitmproxy as a proxy (default: `127.0.0.1:8080`), then browse the Kujiale website.

### Post-Processing

After capturing the content, run the post-processing script to rewrite URLs and download additional resources:

```bash
make post-process
```

### Serving the Mirror

To start the local HTTP server:

```bash
make serve
```

The server will start at http://localhost:8000.

### Other Commands

- Format the code:
  ```bash
  make format
  ```

- Check formatting:
  ```bash
  make format-check
  ```

## Configuration

The following constants can be modified in the scripts:

- `BASE_DIR` / `WEBROOT_DIR`: The directory where mirrored content is stored
- `MAIN_DOMAIN`: The main domain to exclude from path rewriting
- `EXCLUDE_REWRITE`: List of domains to exclude from URL rewriting
