.PHONY: format format-check help run clean serve

PYTHON_FILES := save_responses.py post_process.py
WEBROOT_DIR := ./webroot

help:
	@echo "Available targets:"
	@echo "  format       - Format Python files using yapf"
	@echo "  format-check - Check if Python files are correctly formatted"
	@echo "  run          - Run the local server for proxied content"
	@echo "  serve        - Start the HTTP server"
	@echo "  clean        - Remove generated files"
	@echo "  help         - Show this help message"

format:
	@echo "Formatting Python files..."
	@yapf -i $(PYTHON_FILES)
	@echo "Done."

format-check:
	@echo "Checking Python formatting..."
	@yapf --diff $(PYTHON_FILES) || (echo "Some files need formatting. Run 'make format'" && exit 1)

run: serve

serve:
	@echo "Starting local server..."
	@mkdir -p $(WEBROOT_DIR)
	@go run serve.go

post-process:
	@echo "Post-processing downloaded files..."
	@mkdir -p $(WEBROOT_DIR)
	@python3 post_process.py
