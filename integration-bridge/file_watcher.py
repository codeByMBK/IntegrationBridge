"""
File watcher for IntegrationBridge.

Monitors /app/file_drop for incoming XML invoice files, parses them,
forwards the data to the downstream REST API, and moves processed files
into /app/file_drop/processed/.
"""

import os
import shutil
import time
import xml.etree.ElementTree as ET

import requests
import structlog
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = structlog.get_logger(__name__)

FILE_DROP_DIR = "/app/file_drop"
PROCESSED_DIR = "/app/file_drop/processed"
DOWNSTREAM_URL = "http://downstream-api:8001/invoices"


class InvoiceFileHandler(FileSystemEventHandler):
    """Handles new XML file events in the file_drop directory."""

    def on_created(self, event):
        # Ignore directory events and non-XML files.
        if event.is_directory:
            return
        if not event.src_path.endswith(".xml"):
            return

        filepath = event.src_path
        log = logger.bind(filepath=filepath)
        log.info("file_detected")

        # Give the writer a moment to finish flushing the file.
        time.sleep(0.5)

        try:
            self._process_file(filepath, log)
        except Exception as exc:
            log.error("file_processing_error", detail=str(exc))

    def _process_file(self, filepath: str, log) -> None:
        tree = ET.parse(filepath)
        root = tree.getroot()

        payload = {
            "invoice_id": root.findtext("invoice_id", "").strip(),
            "vendor": root.findtext("vendor", "").strip(),
            "amount": float(root.findtext("amount", "0").strip()),
            "currency": root.findtext("currency", "").strip(),
            "date": root.findtext("date", "").strip(),
        }

        log.info("file_parsed", payload=payload)

        resp = requests.post(DOWNSTREAM_URL, json=payload, timeout=10)
        resp.raise_for_status()

        log.info("file_forwarded", status_code=resp.status_code)

        # Move to processed directory on success.
        dest = os.path.join(PROCESSED_DIR, os.path.basename(filepath))
        shutil.move(filepath, dest)
        log.info("file_moved_to_processed", dest=dest)


def start_file_watcher() -> Observer:
    """
    Start the watchdog observer as a daemon thread.

    Returns the running Observer so the caller can stop it if needed.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    handler = InvoiceFileHandler()
    observer = Observer()
    observer.schedule(handler, path=FILE_DROP_DIR, recursive=False)

    # Daemon thread — dies automatically when the main process exits.
    observer.daemon = True
    observer.start()

    logger.info("file_watcher_started", watch_dir=FILE_DROP_DIR)
    return observer
