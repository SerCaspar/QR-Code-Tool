# main.py

import gui
import logging
import sys
import codecs

"""
This is the entry point of the application. It configures logging and launches the GUI.
"""

# Remove any previously configured handlers.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create a StreamHandler that writes to sys.stdout with UTF‑8 encoding.
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
# Wrap sys.stdout so that the handler writes using UTF-8.
stream_handler.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# Configure logging to write both to a file (with UTF-8) and the stream handler.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("qr_processor.log", encoding='utf-8'),
        stream_handler
    ]
)

def main():
    gui.main()

if __name__ == '__main__':
    main()