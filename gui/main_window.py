"""Main application window — toolbar, status bar, two-stage processing.

Supports both manual and automatic (inbox monitoring) workflows.
"""

import logging
from collections import deque
from pathlib import Path
from typing import Deque, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedLayout,
    QToolBar,
    QWidget,
)

from core.book_assembler import BookAssembler
from core.config import Config, save_config
from core.page_cache import list_cached_pages
from gui.image_review_widget import ImageReviewWidget
from gui.inbox_monitor import InboxMonitor
from gui.page_viewer import PageViewer
from gui.preferences_dialog import PreferencesDialog
from gui.processing_widget import ProcessingWidget
from gui.workers import ExtractionWorker, OCRWorker

logger = logging.getLogger(__name__)

_IDX_PLACEHOLDER = 0
_IDX_PROCESSING = 1
_IDX_IMAGE_REVIEW = 2
_IDX_PAGE_VIEWER = 3

_SAVE_FILTERS = "Text Files (*.txt);;Markdown (*.md);;EPUB (*.epub)"


class MainWindow(QMainWindow):
    """Top-level window with toolbar, status bar, and stacked central area."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._current_pdf_path: Optional[Path] = None
        self._page_texts: List[str] = []
        self._is_processing: bool = False
        self._worker: Optional[ExtractionWorker | OCRWorker] = None
        self._cache_dir: Optional[Path] = None
        self._auto_mode: bool = False
        self._inbox_queue: Deque[Path] = deque()

        self.setWindowTitle("AuraLens")
        self.resize(1200, 800)

        self._setup_central_widget()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_inbox_monitor()
        self._update_action_states()

    # ── Central widget ──────────────────────────────────────────────

    def _setup_central_widget(self) -> None:
        """Create stacked layout with all view widgets."""
        self._central = QWidget()
        self._stack = QStackedLayout(self._central)

        self._placeholder = QLabel("Open a PDF to begin")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._placeholder)        # 0

        self._processing_widget = ProcessingWidget()
        self._stack.addWidget(self._processing_widget)   # 1

        self._image_review_widget = ImageReviewWidget()
        self._image_review_widget.continue_requested.connect(
            self._on_continue_to_ocr
        )
        self._stack.addWidget(self._image_review_widget)  # 2

        self._page_viewer = PageViewer()
        self._page_viewer.re_scan_requested.connect(self._on_re_scan_page)
        self._stack.addWidget(self._page_viewer)          # 3

        self.setCentralWidget(self._central)

    # ── Toolbar ─────────────────────────────────────────────────────

    def _setup_toolbar(self) -> None:
        """Create toolbar with Open PDF, Process, Save Book, Settings."""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._action_open = toolbar.addAction("Open PDF")
        self._action_open.triggered.connect(self._on_open_pdf)

        self._action_process = toolbar.addAction("Process")
        self._action_process.triggered.connect(self._on_process)

        self._action_save = toolbar.addAction("Save Book")
        self._action_save.triggered.connect(self._on_save_book)

        toolbar.addSeparator()

        self._action_settings = toolbar.addAction("Settings")
        self._action_settings.triggered.connect(self._on_settings)

    # ── Status bar ──────────────────────────────────────────────────

    def _setup_status_bar(self) -> None:
        """Add persistent status label."""
        self._status_label = QLabel("Ready")
        self.statusBar().addPermanentWidget(self._status_label)

    def _set_status(self, text: str) -> None:
        """Update the persistent status label."""
        self._status_label.setText(text)

    # ── Inbox monitor ───────────────────────────────────────────────

    def _setup_inbox_monitor(self) -> None:
        """Create and optionally start the inbox monitor."""
        self._inbox_monitor = InboxMonitor(parent=self)
        self._inbox_monitor.pdf_detected.connect(self._on_inbox_pdf_detected)

        if self._config.inbox_dir.strip():
            self._inbox_monitor.start(self._config.inbox_dir)

    def _on_inbox_pdf_detected(self, pdf_path: object) -> None:
        """New PDF arrived in inbox — queue it for auto-processing."""
        path = Path(str(pdf_path))
        self._inbox_queue.append(path)
        queue_size = len(self._inbox_queue)
        logger.info("Inbox: queued %s (%d in queue)", path.name, queue_size)
        self._set_status(f"Inbox: {path.name} queued ({queue_size} pending)")
        self._process_next_in_queue()

    def _process_next_in_queue(self) -> None:
        """Start processing the next queued inbox PDF if idle."""
        if self._is_processing or not self._inbox_queue:
            return

        if not self._can_auto_process():
            self._set_status("Inbox: waiting — configure model and API first")
            return

        pdf_path = self._inbox_queue.popleft()
        if not pdf_path.exists():
            logger.warning("Inbox: file vanished: %s", pdf_path)
            self._process_next_in_queue()
            return

        self._auto_mode = True
        self._current_pdf_path = pdf_path
        self._page_texts.clear()
        self._set_status(f"Auto-processing: {pdf_path.name}")
        self._start_extraction()

    def _can_auto_process(self) -> bool:
        """Check if config is sufficient for automatic processing."""
        return bool(
            self._config.model_name.strip()
            and self._config.api_url.strip()
        )

    # ── Action state management ─────────────────────────────────────

    def _update_action_states(self) -> None:
        """Enable/disable toolbar actions based on current state."""
        has_pdf = self._current_pdf_path is not None
        has_pages = len(self._page_texts) > 0

        self._action_open.setEnabled(not self._is_processing)
        self._action_process.setEnabled(has_pdf and not self._is_processing)
        self._action_save.setEnabled(has_pages and not self._is_processing)
        self._action_settings.setEnabled(not self._is_processing)

    # ── Validation ──────────────────────────────────────────────────

    def _validate_for_processing(self) -> bool:
        """Check config has required fields. Show warning if not."""
        if not self._config.model_name.strip():
            QMessageBox.warning(
                self, "Configuration Error",
                "Model name is not set. Open Settings to configure it.",
            )
            return False
        if not self._config.api_url.strip():
            QMessageBox.warning(
                self, "Configuration Error",
                "API URL is not set. Open Settings to configure it.",
            )
            return False
        return True

    # ── Slots: toolbar ──────────────────────────────────────────────

    def _on_open_pdf(self) -> None:
        """Open a file dialog to select a PDF."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        if not path:
            return

        self._auto_mode = False
        self._current_pdf_path = Path(path)
        self._page_texts.clear()
        self._set_status(f"PDF loaded: {self._current_pdf_path.name}")
        self._update_action_states()

    def _on_process(self) -> None:
        """Start two-stage processing: extraction then OCR."""
        if not self._current_pdf_path or not self._validate_for_processing():
            return
        self._auto_mode = False
        self._start_extraction()

    def _on_save_book(self) -> None:
        """Save processed text in chosen format."""
        texts = self._page_viewer.get_all_texts()
        if not texts:
            return

        default_dir = self._get_save_default_dir()
        default_name = (
            self._current_pdf_path.stem if self._current_pdf_path else "book"
        )
        default_path = str(Path(default_dir) / f"{default_name}.txt")

        path, chosen_filter = QFileDialog.getSaveFileName(
            self, "Save Book", default_path, _SAVE_FILTERS,
        )
        if not path:
            return

        self._save_in_format(texts, Path(path), chosen_filter)

    def _on_settings(self) -> None:
        """Open preferences dialog and apply changes."""
        old_inbox = self._config.inbox_dir
        dialog = PreferencesDialog(self._config, parent=self)
        if dialog.run():
            self._config = dialog.get_config()
            save_config(self._config)
            self._apply_inbox_config_change(old_inbox)

    def _apply_inbox_config_change(self, old_inbox: str) -> None:
        """Restart inbox monitor if inbox_dir changed."""
        new_inbox = self._config.inbox_dir
        if new_inbox != old_inbox:
            self._inbox_monitor.update_path(new_inbox)

    # ── Stage 1: Extraction ─────────────────────────────────────────

    def _start_extraction(self) -> None:
        """Extract PDF pages to cache folder."""
        assert self._current_pdf_path is not None

        self._is_processing = True
        self._page_texts.clear()
        self._update_action_states()
        self._stack.setCurrentIndex(_IDX_PROCESSING)

        self._worker = ExtractionWorker(
            pdf_path=self._current_pdf_path,
            dpi=self._config.pdf_dpi,
            max_pixels=self._config.max_image_pixels,
            jpeg_quality=self._config.jpeg_quality,
        )
        self._worker.page_extracted.connect(self._on_page_extracted)
        self._worker.extraction_finished.connect(self._on_extraction_finished)
        self._processing_widget.cancel_requested.connect(self._worker.cancel)
        self._processing_widget.start(
            self._current_pdf_path.name, total_pages=0,
        )
        self._set_status(f"Extracting: {self._current_pdf_path.name}")
        self._worker.start()

    def _on_page_extracted(self, page_num: int, total: int) -> None:
        """Update progress during extraction."""
        self._processing_widget.update_page(page_num, total)
        self._set_status(f"Extracting page {page_num}/{total}")

    def _on_extraction_finished(self, cache_dir: str, total: int) -> None:
        """Extraction done — show review or auto-continue to OCR."""
        self._cache_dir = Path(cache_dir)
        self._is_processing = False
        self._worker = None
        self._update_action_states()

        if self._auto_mode:
            self._on_continue_to_ocr()
        else:
            self._image_review_widget.show_ready(self._cache_dir, total)
            self._stack.setCurrentIndex(_IDX_IMAGE_REVIEW)
            self._set_status(
                f"Extracted {total} pages — review before OCR"
            )

    # ── Stage 2: OCR ────────────────────────────────────────────────

    def _on_continue_to_ocr(self) -> None:
        """User approved images (or auto-mode) — start OCR worker."""
        assert self._cache_dir is not None

        page_paths = list_cached_pages(self._cache_dir)
        if not page_paths:
            self._set_status("No images found in cache folder")
            return

        self._is_processing = True
        self._page_texts.clear()
        self._update_action_states()
        self._stack.setCurrentIndex(_IDX_PROCESSING)

        cfg = self._config
        
        # Resume support: check for already processed pages in the output file
        output_path = self._get_incremental_path()
        assembler = BookAssembler()
        skipped_pages = assembler.get_completed_pages(output_path)
        if skipped_pages:
            logger.info("Resuming OCR. Skipping %d pages: %s", len(skipped_pages), sorted(skipped_pages))

        self._worker = OCRWorker(
            page_paths=page_paths,
            api_url=cfg.api_url,
            api_key=cfg.api_key,
            model_name=cfg.model_name,
            timeout=cfg.timeout,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            system_prompt=cfg.system_prompt,
            skip_pages=skipped_pages,
        )
        self._worker.page_started.connect(self._on_page_started)
        self._worker.page_completed.connect(self._on_page_completed)
        self._worker.page_error.connect(self._on_page_error)
        self._worker.processing_finished.connect(self._on_ocr_finished)
        self._processing_widget.cancel_requested.connect(self._worker.cancel)
        self._processing_widget.start(
            f"OCR: {self._cache_dir.name}", len(page_paths),
        )
        self._set_status(f"Starting OCR (Resuming {len(skipped_pages)} pages)...")
        self._worker.start()

    def _on_page_started(self, page_num: int, total: int) -> None:
        """Update progress when OCR starts a page."""
        self._processing_widget.update_page(page_num - 1, total)
        self._set_status(f"OCR page {page_num}/{total}")

    def _on_page_completed(
        self, page_num: int, total: int, text: str
    ) -> None:
        """Store extracted text and update progress."""
        self._ensure_page_slots(page_num)
        self._page_texts[page_num - 1] = text
        self._processing_widget.update_page(page_num, total)
        self._set_status(f"OCR done: page {page_num}/{total}")
        self._auto_save_incremental()

    def _on_page_error(self, page_num: int, error_msg: str) -> None:
        """Store error marker for failed page."""
        self._ensure_page_slots(page_num)
        self._page_texts[page_num - 1] = f"[ERROR: {error_msg}]"
        self._set_status(f"Error on page {page_num}: {error_msg}")

    def _on_ocr_finished(self) -> None:
        """OCR done — auto-save or switch to page viewer."""
        self._is_processing = False
        self._worker = None
        self._processing_widget.finish()
        self._update_action_states()

        ok_count = sum(
            1 for t in self._page_texts
            if t and not t.startswith("[ERROR")
        )

        if self._auto_mode:
            self._auto_save_to_outbox()
            self._set_status(
                f"Auto: saved {ok_count} pages — "
                f"{len(self._inbox_queue)} remaining"
            )
            self._auto_mode = False
            self._process_next_in_queue()
        else:
            if self._page_texts and self._cache_dir:
                page_paths = list_cached_pages(self._cache_dir)
                self._page_viewer.load_pages(page_paths, self._page_texts)
                self._stack.setCurrentIndex(_IDX_PAGE_VIEWER)
            self._set_status(f"Done: {ok_count} pages processed")

    def _on_re_scan_page(self, page_num: int) -> None:
        """Re-process a single page triggered by the viewer."""
        if not self._cache_dir or self._is_processing:
            logger.warning("Cannot re-scan: busy or no cache dir")
            return

        page_paths = list_cached_pages(self._cache_dir)
        if page_num < 1 or page_num > len(page_paths):
            return

        # We only process the one page
        target_path = page_paths[page_num - 1]
        logger.info("Re-scanning page %d: %s", page_num, target_path)

        cfg = self._config
        self._is_processing = True
        self._set_status(f"Re-scanning page {page_num}...")
        
        # Disable actions during re-scan (optional, but good for safety)
        self._update_action_states()

        # Create a ephemeral worker just for this page
        # Note: We must verify if we need to keep a reference to avoid GC
        self._worker = OCRWorker(
            page_paths=[target_path],
            api_url=cfg.api_url,
            api_key=cfg.api_key,
            model_name=cfg.model_name,
            timeout=cfg.timeout,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            system_prompt=cfg.system_prompt,
        )
        # We need a custom completion handler that knows which page it was
        # But OCRWorker emits page_completed(page_num, total, text)
        # However, since we passed a list of 1, page_num will be 1.
        # We need to map it back to the absolute page_num.
        
        # Solution: Use a lambda or partial, OR just rely on the fact that we know 
        # which page we requested? 
        # Actually, OCRWorker emits relative page number. 
        # Let's attach the absolute page_num to the worker or closure.
        
        self._worker.page_completed.connect(
            lambda _, __, text: self._on_re_scan_completed(page_num, text)
        )
        self._worker.page_error.connect(
            lambda _, err: self._on_page_error(page_num, err)
        )
        
        # We also need to finish the worker state
        self._worker.processing_finished.connect(self._on_re_scan_finished)
        
        self._worker.start()

    def _on_re_scan_completed(self, page_num: int, text: str) -> None:
        """Handle new text from re-scan."""
        logger.info("Re-scan finished for page %d", page_num)
        self._page_texts[page_num - 1] = text
        self._auto_save_incremental()
        # Update the viewer with the new text immediately
        self._page_viewer.load_pages(
            list_cached_pages(self._cache_dir), self._page_texts
        )
        # Restore view to that page
        self._page_viewer._navigate_to(page_num)
        self._set_status(f"Re-scan complete: Page {page_num}")

    def _on_re_scan_finished(self) -> None:
        """Cleanup after re-scan."""
        self._is_processing = False
        self._worker = None
        self._update_action_states()

    # ── Auto-save (inbox mode & incremental) ───────────────────────

    def _auto_save_to_outbox(self) -> None:
        """Final save to outbox_dir as .txt (inbox auto-mode)."""
        self._save_output_file()

    def _auto_save_incremental(self) -> None:
        """Incrementally save progress to the output file."""
        # Only save if we have a path or specific setting
        # For now, we mirror the logic of auto-save but for all modes if desired
        # Or strictly follow the plan: overwrite the destination file
        if not self._current_pdf_path:
            return
        
        try:
            path = self._get_incremental_path()
            assembler = BookAssembler()
            # We save everything we have so far (including empty slots/errors)
            # Filter out None/Empty for cleaner partials? 
            # No, keep structure so page numbers align.
            # But BookAssembler treats list index as page num.
            assembler.save_to_file(self._page_texts, path)
        except Exception as e:
            logger.error("Incremental save failed: %s", e)

    def _get_incremental_path(self) -> Path:
        """Determine where to save the incremental book."""
        outbox = self._config.outbox_dir.strip()
        if not outbox:
            outbox = str(self._current_pdf_path.parent)
        
        # We use the final filename so the user sees it grow.
        # If we wanted a temp name, we'd append .part
        return Path(outbox) / f"{self._current_pdf_path.stem}.txt"

    def _save_output_file(self) -> None:
        """Helper to save current text to the configured output."""
        if not self._page_texts or not self._current_pdf_path:
            return

        output_path = self._get_incremental_path()
        assembler = BookAssembler()
        assembler.save_to_file(self._page_texts, output_path)
        logger.info("Auto-saved: %s", output_path)

    # ── Save helpers ────────────────────────────────────────────────

    def _get_save_default_dir(self) -> str:
        """Return outbox_dir if set, else PDF's parent directory."""
        if self._config.outbox_dir:
            return self._config.outbox_dir
        if self._current_pdf_path:
            return str(self._current_pdf_path.parent)
        return ""

    def _save_in_format(
        self, texts: List[str], path: Path, chosen_filter: str
    ) -> None:
        """Dispatch to correct BookAssembler method based on format."""
        assembler = BookAssembler()
        title = path.stem

        if path.suffix == ".epub" or "EPUB" in chosen_filter:
            assembler.save_as_epub(texts, path, title=title)
        elif path.suffix == ".md" or "Markdown" in chosen_filter:
            assembler.save_as_markdown(texts, path)
        else:
            assembler.save_to_file(texts, path)

        self._set_status(f"Saved: {path.name} ({len(texts)} pages)")

    # ── Helpers ─────────────────────────────────────────────────────

    def _ensure_page_slots(self, page_num: int) -> None:
        """Extend _page_texts list to accommodate page_num (1-indexed)."""
        while len(self._page_texts) < page_num:
            self._page_texts.append("")
