"""Main application window — toolbar, status bar, two-stage processing.

Supports both manual and automatic (inbox monitoring) workflows.
Refactored for MCCC compliance - delegates to specialized modules.
"""

import logging
from pathlib import Path
from typing import List, Optional

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

from core.config import Config, save_config
from core.config_validator import ConfigValidator
from core.workflow_orchestrator import WorkflowOrchestrator
from gui.image_review_widget import ImageReviewWidget
from gui.inbox_coordinator import InboxCoordinator
from gui.inbox_monitor import InboxMonitor
from gui.page_viewer import PageViewer
from gui.preferences_dialog import PreferencesDialog
from gui.processing_widget import ProcessingWidget
from gui.save_manager import SaveManager
from gui.workers import ExtractionWorker, OCRWorker

logger = logging.getLogger(__name__)

_IDX_PLACEHOLDER = 0
_IDX_PROCESSING = 1
_IDX_IMAGE_REVIEW = 2
_IDX_PAGE_VIEWER = 3

_SAVE_FILTERS = "Text Files (*.txt);;Markdown (*.md);;EPUB (*.epub)"


class MainWindow(QMainWindow):
    """Top-level window with toolbar, status bar, and stacked central area.
    
    Responsibilities:
    - UI setup and layout
    - Signal routing between components
    - User interaction handling
    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        
        # State
        self._current_pdf_path: Optional[Path] = None
        self._page_texts: List[str] = []
        self._is_processing: bool = False
        self._worker: Optional[ExtractionWorker | OCRWorker] = None
        self._cache_dir: Optional[Path] = None
        self._auto_mode: bool = False

        # Extracted modules
        self._orchestrator = WorkflowOrchestrator(config)
        self._save_manager = SaveManager(config)
        self._inbox_coordinator = InboxCoordinator(config, parent=self)

        # UI setup
        self.setWindowTitle("AuraLens")
        self.resize(1200, 800)

        self._setup_central_widget()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_inbox_monitor()
        self._connect_inbox_signals()
        self._update_action_states()

    # ── Central widget ──────────────────────────────────────────────

    def _setup_central_widget(self) -> None:
        """Create stacked layout with all view widgets."""
        self._central = QWidget()
        self._stack = QStackedLayout(self._central)

        self._placeholder = QLabel("Open a PDF to begin")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._placeholder)

        self._processing_widget = ProcessingWidget()
        self._stack.addWidget(self._processing_widget)

        self._image_review_widget = ImageReviewWidget()
        self._image_review_widget.continue_requested.connect(
            self._on_continue_to_ocr
        )
        self._stack.addWidget(self._image_review_widget)

        self._page_viewer = PageViewer()
        self._page_viewer.re_scan_requested.connect(self._on_re_scan_page)
        self._stack.addWidget(self._page_viewer)

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
        self._inbox_monitor.pdf_detected.connect(
            self._on_inbox_pdf_detected
        )

        if self._config.inbox_dir.strip():
            self._inbox_monitor.start(self._config.inbox_dir)

    def _connect_inbox_signals(self) -> None:
        """Connect inbox coordinator signals."""
        self._inbox_coordinator.status_updated.connect(self._set_status)
        self._inbox_coordinator.processing_requested.connect(
            self._on_inbox_processing_requested
        )

    def _on_inbox_pdf_detected(self, pdf_path: object) -> None:
        """New PDF arrived in inbox — queue it."""
        path = Path(str(pdf_path))
        self._inbox_coordinator.queue_pdf(path)
        self._inbox_coordinator.process_next_if_ready(self._is_processing)

    def _on_inbox_processing_requested(self, pdf_path: Path) -> None:
        """Inbox coordinator requests processing of a PDF."""
        self._auto_mode = True
        self._current_pdf_path = pdf_path
        self._page_texts.clear()
        self._start_extraction()

    # ── Action state management ─────────────────────────────────────

    def _update_action_states(self) -> None:
        """Enable/disable toolbar actions based on current state."""
        has_pdf = self._current_pdf_path is not None
        has_pages = len(self._page_texts) > 0

        self._action_open.setEnabled(not self._is_processing)
        self._action_process.setEnabled(has_pdf and not self._is_processing)
        self._action_save.setEnabled(has_pages and not self._is_processing)
        self._action_settings.setEnabled(not self._is_processing)

    # ── User actions ────────────────────────────────────────────────

    def _on_open_pdf(self) -> None:
        """Open a file dialog to select a PDF."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        if path:
            self._current_pdf_path = Path(path)
            self._page_texts.clear()
            self._auto_mode = False
            self._set_status(f"Loaded: {self._current_pdf_path.name}")
            self._update_action_states()

    def _on_process(self) -> None:
        """Start two-stage processing: extraction then OCR."""
        if not self._validate_config():
            return
        self._start_extraction()

    def _on_save_book(self) -> None:
        """Save processed text in chosen format."""
        if not self._page_texts:
            return

        default_dir = self._save_manager.get_default_save_dir(
            self._current_pdf_path
        )
        path, chosen_filter = QFileDialog.getSaveFileName(
            self, "Save Book", default_dir, _SAVE_FILTERS
        )

        if path:
            self._save_manager.save_as_format(
                self._page_texts, Path(path), chosen_filter
            )
            self._set_status(f"Saved: {Path(path).name}")

    def _on_settings(self) -> None:
        """Open preferences dialog and apply changes."""
        old_inbox = self._config.inbox_dir
        dialog = PreferencesDialog(self._config, parent=self)
        if dialog.exec():
            save_config(self._config)
            self._apply_inbox_config_change(old_inbox)

    # ── Validation ──────────────────────────────────────────────────

    def _validate_config(self) -> bool:
        """Validate config and show warning if invalid."""
        is_valid, error_msg = ConfigValidator.validate_for_ocr(self._config)
        if not is_valid:
            QMessageBox.warning(
                self, "Configuration Error", error_msg
            )
        return is_valid

    def _apply_inbox_config_change(self, old_inbox: str) -> None:
        """Restart inbox monitor if inbox_dir changed."""
        if old_inbox != self._config.inbox_dir:
            self._inbox_monitor.stop()
            if self._config.inbox_dir.strip():
                self._inbox_monitor.start(self._config.inbox_dir)

    # ── Extraction stage ────────────────────────────────────────────

    def _start_extraction(self) -> None:
        """Extract PDF pages to cache folder."""
        self._cache_dir = self._orchestrator.get_cache_dir_for_pdf(
            self._current_pdf_path
        )
        params = self._orchestrator.get_extraction_params()

        self._is_processing = True
        self._update_action_states()
        self._stack.setCurrentIndex(_IDX_PROCESSING)
        self._processing_widget.set_stage("Extracting pages...")

        self._worker = ExtractionWorker(
            pdf_path=self._current_pdf_path,
            **params
        )
        self._worker.page_extracted.connect(self._on_page_extracted)
        self._worker.extraction_finished.connect(self._on_extraction_finished)
        self._worker.start()

    def _on_page_extracted(self, page_num: int, total: int) -> None:
        """Update progress during extraction."""
        self._processing_widget.set_progress(page_num, total)
        self._set_status(f"Extracted page {page_num}/{total}")

    def _on_extraction_finished(self, cache_dir: str, total: int) -> None:
        """Extraction done — show review or auto-continue to OCR."""
        self._cache_dir = Path(cache_dir)
        self._worker = None

        if self._auto_mode:
            self._on_continue_to_ocr()
        else:
            page_paths = self._orchestrator.get_page_paths_from_cache(
                self._cache_dir
            )
            self._image_review_widget.load_images(page_paths)
            self._stack.setCurrentIndex(_IDX_IMAGE_REVIEW)
            self._set_status(f"Review {total} extracted images")

    # ── OCR stage ───────────────────────────────────────────────────

    def _on_continue_to_ocr(self) -> None:
        """User approved images — start OCR."""
        page_paths = self._orchestrator.get_page_paths_from_cache(
            self._cache_dir
        )
        if not page_paths:
            self._set_status("No images found")
            return

        self._start_ocr_worker(page_paths)

    def _start_ocr_worker(self, page_paths: List[Path]) -> None:
        """Create and start OCR worker with resume support."""
        params = self._orchestrator.get_ocr_params()
        
        # Calculate resume pages
        output_path = self._orchestrator.get_incremental_save_path(
            self._current_pdf_path
        )
        skip_pages = self._orchestrator.calculate_resume_pages(output_path)

        self._stack.setCurrentIndex(_IDX_PROCESSING)
        self._processing_widget.set_stage("Processing with VLM...")

        self._worker = OCRWorker(
            page_paths=page_paths,
            skip_pages=skip_pages,
            **params
        )
        self._worker.page_started.connect(self._on_page_started)
        self._worker.page_completed.connect(self._on_page_completed)
        self._worker.page_error.connect(self._on_page_error)
        self._worker.processing_finished.connect(self._on_ocr_finished)
        self._worker.start()

    def _on_page_started(self, page_num: int, total: int) -> None:
        """Update progress when OCR starts a page."""
        self._processing_widget.set_progress(page_num, total)
        self._set_status(f"OCR page {page_num}/{total}")

    def _on_page_completed(
        self, page_num: int, total: int, text: str
    ) -> None:
        """Store extracted text and update progress."""
        self._ensure_page_slots(page_num)
        self._page_texts[page_num - 1] = text
        self._save_manager.save_incremental(
            self._page_texts, self._current_pdf_path
        )

    def _on_page_error(self, page_num: int, error_msg: str) -> None:
        """Store error marker for failed page."""
        self._ensure_page_slots(page_num)
        self._page_texts[page_num - 1] = f"[ERROR: {error_msg}]"

    def _on_ocr_finished(self) -> None:
        """OCR done — auto-save or switch to page viewer."""
        self._worker = None
        self._is_processing = False
        self._update_action_states()

        ok_count = sum(
            1 for t in self._page_texts if t and not t.startswith("[ERROR")
        )

        if self._auto_mode:
            self._save_manager.auto_save_to_outbox(
                self._page_texts, self._current_pdf_path
            )
            self._inbox_coordinator.process_next_if_ready(
                is_processing=False
            )
        else:
            page_paths = self._orchestrator.get_page_paths_from_cache(
                self._cache_dir
            )
            self._page_viewer.load_pages(page_paths, self._page_texts)
            self._stack.setCurrentIndex(_IDX_PAGE_VIEWER)

        self._set_status(f"Done: {ok_count} pages processed")

    # ── Re-scan single page ─────────────────────────────────────────

    def _on_re_scan_page(self, page_num: int) -> None:
        """Re-process a single page triggered by the viewer."""
        if not self._can_rescan(page_num):
            return
        self._execute_rescan(page_num)

    def _can_rescan(self, page_num: int) -> bool:
        """Validate re-scan request."""
        if not self._cache_dir or self._is_processing:
            logger.warning("Cannot re-scan: busy or no cache dir")
            return False

        page_paths = self._orchestrator.get_page_paths_from_cache(
            self._cache_dir
        )
        if page_num < 1 or page_num > len(page_paths):
            return False

        return True

    def _execute_rescan(self, page_num: int) -> None:
        """Execute re-scan for a single page."""
        page_paths = self._orchestrator.get_page_paths_from_cache(
            self._cache_dir
        )
        target_path = page_paths[page_num - 1]
        logger.info("Re-scanning page %d: %s", page_num, target_path)

        params = self._orchestrator.get_ocr_params()
        self._is_processing = True
        self._set_status(f"Re-scanning page {page_num}...")
        self._update_action_states()

        self._worker = OCRWorker(
            page_paths=[target_path],
            **params
        )
        self._worker.page_completed.connect(
            lambda _, __, text: self._on_re_scan_completed(page_num, text)
        )
        self._worker.page_error.connect(
            lambda _, err: self._on_page_error(page_num, err)
        )
        self._worker.processing_finished.connect(self._on_re_scan_finished)
        self._worker.start()

    def _on_re_scan_completed(self, page_num: int, text: str) -> None:
        """Handle new text from re-scan."""
        logger.info("Re-scan finished for page %d", page_num)
        self._page_texts[page_num - 1] = text
        self._save_manager.save_incremental(
            self._page_texts, self._current_pdf_path
        )
        
        page_paths = self._orchestrator.get_page_paths_from_cache(
            self._cache_dir
        )
        self._page_viewer.load_pages(page_paths, self._page_texts)
        self._page_viewer._navigate_to(page_num)
        self._set_status(f"Re-scan complete: Page {page_num}")

    def _on_re_scan_finished(self) -> None:
        """Cleanup after re-scan."""
        self._is_processing = False
        self._worker = None
        self._update_action_states()

    # ── Utilities ───────────────────────────────────────────────────

    def _ensure_page_slots(self, page_num: int) -> None:
        """Extend _page_texts list to accommodate page_num (1-indexed)."""
        while len(self._page_texts) < page_num:
            self._page_texts.append("")
