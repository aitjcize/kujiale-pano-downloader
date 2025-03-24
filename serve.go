package main

import (
	"fmt"
	"io"
	"log"
	"mime"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

const (
	BASE_DIR    = "./webroot/"
	MAIN_DOMAIN = "www.kujiale.com"
)

type CustomHandler struct {
	http.Handler
}

func translatePath(path string) string {
	parsedURL, err := url.Parse(path)
	if err != nil {
		log.Printf("Error parsing URL: %v", err)
		return filepath.Join(BASE_DIR, path)
	}

	pathFile := strings.TrimPrefix(parsedURL.Path, "/")

	// Special handling for domain paths (*.kujiale.com except www.kujiale.com)
	domainRegex := regexp.MustCompile(`^([^/]+\.kujiale\.com)(/.*)?$`)
	domainMatch := domainRegex.FindStringSubmatch(pathFile)

	if len(domainMatch) > 0 {
		domain := domainMatch[1]
		// Skip main domain
		if domain == MAIN_DOMAIN {
			fullPath := filepath.Join(BASE_DIR, pathFile)
			fileInfo, err := os.Stat(fullPath)
			if err == nil && fileInfo.IsDir() {
				fullPath = filepath.Join(fullPath, "index.html")
			}
			return fullPath
		}

		subpath := ""
		if len(domainMatch) > 2 && domainMatch[2] != "" {
			subpath = strings.TrimPrefix(domainMatch[2], "/")
		}
		pathFile = fmt.Sprintf("%s/%s", domain, subpath)
	}

	// Check if path has query components for CDN domains
	if parsedURL.RawQuery != "" &&
		strings.Contains(path, ".kujiale.com/") &&
		!strings.Contains(path, MAIN_DOMAIN) &&
		!strings.Contains(path, "panojson-oss.kujiale.com") {
		querySuffix := "__" + strings.ReplaceAll(
			strings.ReplaceAll(
				strings.ReplaceAll(
					strings.ReplaceAll(
						parsedURL.RawQuery,
						"/", "_"),
					":", "_"),
				"?", "_"),
			"%7C", "|")
		pathFile += querySuffix
	}

	fullPath := filepath.Join(BASE_DIR, pathFile)
	fileInfo, err := os.Stat(fullPath)
	if err == nil && fileInfo.IsDir() {
		fullPath = filepath.Join(fullPath, "index.html")
	}

	fmt.Printf("Serving: %s -> %s\n", path, fullPath)
	return fullPath
}

func getContentType(filename string) string {
	ext := filepath.Ext(filename)
	if ext == "" {
		return ""
	}

	// Use standard library mime package to detect content type
	mimeType := mime.TypeByExtension(ext)
	if mimeType != "" {
		return mimeType
	}

	// Fallback for common types
	switch strings.ToLower(ext) {
	case ".html", ".htm":
		return "text/html"
	case ".js":
		return "application/javascript"
	case ".css":
		return "text/css"
	case ".json":
		return "application/json"
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".gif":
		return "image/gif"
	case ".webp":
		return "image/webp"
	case ".svg":
		return "image/svg+xml"
	case ".txt":
		return "text/plain"
	}

	return ""
}

func (h *CustomHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Connection", "keep-alive")

	if r.Method == "POST" {
		localFile := translatePath(r.URL.String())
		_, err := os.Stat(localFile)

		if err == nil {
			// File exists
			fileInfo, _ := os.Stat(localFile)
			fileSize := fileInfo.Size()

			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("Content-Length", fmt.Sprintf("%d", fileSize))

			file, err := os.Open(localFile)
			if err != nil {
				http.Error(w, "Internal server error", http.StatusInternalServerError)
				return
			}
			defer file.Close()

			io.Copy(w, file)
			fmt.Printf("[POST HIT] %s -> %s\n", r.URL.String(), localFile)
		} else {
			// File doesn't exist
			w.WriteHeader(http.StatusOK)
			fmt.Printf("[POST MISS] %s -> %s\n", r.URL.String(), localFile)
		}
	} else {
		// For GET and other methods
		localFile := translatePath(r.URL.String())
		_, err := os.Stat(localFile)

		if err == nil {
			// Set content type based on file extension
			contentType := getContentType(localFile)
			if contentType != "" {
				w.Header().Set("Content-Type", contentType)
			}

			// Open and serve the file
			file, err := os.Open(localFile)
			if err != nil {
				http.Error(w, "Internal server error", http.StatusInternalServerError)
				return
			}
			defer file.Close()

			// Get file info for content length
			fileInfo, _ := os.Stat(localFile)
			w.Header().Set("Content-Length", fmt.Sprintf("%d", fileInfo.Size()))

			io.Copy(w, file)
			fmt.Printf("[GET HIT] %s -> %s\n", r.URL.String(), localFile)
		} else {
			http.NotFound(w, r)
			fmt.Printf("[GET MISS] %s -> %s\n", r.URL.String(), localFile)
		}
	}
}

func main() {
	port := 8000
	handler := &CustomHandler{}

	fmt.Printf("Serving from %s at http://localhost:%d\n", BASE_DIR, port)

	server := &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: handler,
	}

	log.Fatal(server.ListenAndServe())
}
