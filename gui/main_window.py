"""Main application window — toolbar, status bar, two-stage processing.

Supports both manual and automatic (inbox monitoring) workflows.
Refactored for MCCC compliance - delegates to specialized modules.
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from core.config import Config, save_config
from core.config_validator import ConfigValidator
from core.page_cache import save_page_text, list_cached_page_texts
from core.workflow_orchestrator import WorkflowOrchestrator
from gui.inbox_coordinator import InboxCoordinator
from gui.inbox_monitor import InboxMonitor
from gui.processing_widget import ProcessingWidget
from gui.save_manager import SaveManager

from gui.workers import ExtractionWorker, OCRWorker, VLMWorker
from core.book_assembler import BookAssembler

# New UI Components
from gui.modern_window import ModernWindow
from gui.home_screen import HomeScreen
from gui.split_processing_view import SplitProcessingView
from gui.pages.settings_page import SettingsPage
from gui.pages.prompt_tester_page import PromptTesterPage

# Index constants matching _setup_ui order
# 0: Dashboard
# 1: Processing View
# 2: Prompt Container
# 3: Settings
# 4: Workers Status

_SAVE_FILTERS = "Text Files (*.txt);;Markdown (*.md);;EPUB (*.epub)"


class MainWindow(ModernWindow):
    """
    Top-level window implementing 'Modern Dashboard Architecture'.
    - Single Window (No Popups).
    - Stacked Layout.
    - Custom Header.
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

        # Modules
        self._orchestrator = WorkflowOrchestrator(config)
        self._save_manager = SaveManager(config)
        self._inbox_coordinator = InboxCoordinator(config, parent=self)

        # UI Setup
        self.setWindowTitle("AuraLens")
        self.setMinimumSize(1280, 800)
        
        # Setup Central Widget with Header + Stack
        self._setup_ui()
        
        # Status Bar (kept minimal or removed? Reference has none. We keep for status msgs)
        self._setup_status_bar()
        
        self._setup_inbox_monitor()
        self._connect_inbox_signals()
        
        self._restore_window_geometry()

    def _setup_ui(self):
        """Reference Architecture: Header + QStackedWidget."""
        
        # Use _content_area provided by ModernWindow (already set as central widget)
        main_layout = QVBoxLayout(self._content_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Title-bar ⌂ button wired here (ModernWindow emits home_requested)
        self.home_requested.connect(self._on_home)

        # Stacked Content
        self._stack = QStackedLayout()
        
        # Pages
        # Index 0: Dashboard
        self._dashboard_page = HomeScreen()
        self._dashboard_page.action_open_pdf.connect(self._on_open_pdf)
        self._dashboard_page.action_process_pdf.connect(self._on_process_page)
        self._dashboard_page.action_test_prompt.connect(self._on_test_prompt_page)
        self._dashboard_page.action_config.connect(self._on_settings_page)
        self._stack.addWidget(self._dashboard_page)
        
        # Index 1: Processing (Split View)
        self._process_page = SplitProcessingView()
        self._process_page.run_ocr_requested.connect(lambda: self._start_ocr(resume=True))
        self._process_page.accept_book_requested.connect(self._on_accept_book)
        self._process_page.re_scan_requested.connect(self._on_re_scan_page)
        self._process_page.save_page_requested.connect(self._on_save_page_text)
        self._process_page.config_requested.connect(self._on_settings_page)
        self._process_page.home_requested.connect(self._on_home)
        self._stack.addWidget(self._process_page)
        
        # Index 2: Prompt Tester Page
        # Loaded dynamically or instantiated? 
        # Instantiating now requires cache_dir which might be None initially.
        # We'll stick a placeholder or instantiate when needed.
        # For stack, we need a consistent widget. 
        # Let's assume we create it when needed, or use a container.
        self._prompt_container = QWidget()
        self._prompt_layout = QVBoxLayout(self._prompt_container)
        self._stack.addWidget(self._prompt_container)
        
        # Index 3: Settings Page
        self._settings_page = SettingsPage(self._config)
        self._settings_page.home_requested.connect(self._on_home)
        self._settings_page.config_saved.connect(self._on_config_saved)
        self._stack.addWidget(self._settings_page)
        
        # Index 4: Active Worker Progress (Fullscreen or Overlay?)
        # Let's keep ProcessingWidget as a page?
        self._processing_widget = ProcessingWidget()
        self._processing_widget.cancel_requested.connect(self._on_cancel_processing)
        self._stack.addWidget(self._processing_widget)

        main_layout.addLayout(self._stack)

    # ── Navigation Methods ──────────────────────────────────────────

    def _on_home(self):
        self._stack.setCurrentWidget(self._dashboard_page)
        
    def _on_process_page(self):
        # If no PDF, open dialog
        if not self._current_pdf_path:
             self._on_open_pdf()
             if not self._current_pdf_path: return
             
        # Check cache
        if self._orchestrator.is_fully_cached(self._orchestrator.get_cache_dir_for_pdf(self._current_pdf_path)):
             self._load_from_cache()
        else:
             self._start_extraction()

    def _on_test_prompt_page(self):
        if not self._cache_dir or not self._cache_dir.exists():
             QMessageBox.warning(self, "No PDF", "Please Open a PDF first to test prompts.")
             return
             
        # Re-create page to refresh state/images
        # Clear container
        while self._prompt_layout.count():
             child = self._prompt_layout.takeAt(0)
             if child.widget(): child.widget().deleteLater()
             
        page = PromptTesterPage(self._config, self._cache_dir)
        page.home_requested.connect(self._on_home)
        self._prompt_layout.addWidget(page)
        
        self._stack.setCurrentWidget(self._prompt_container)

    def _on_settings_page(self):
        self._stack.setCurrentWidget(self._settings_page)

    def _on_config_saved(self, new_config):
        self._config = new_config
        save_config(self._config)
        # Update orchestrator
        self._orchestrator = WorkflowOrchestrator(self._config)
        from gui.theme_manager import ThemeManager
        ThemeManager.apply_theme(self, ThemeManager.get_current_theme())
        self._on_home()

    # ── Standard Actions ────────────────────────────────────────────

    def _on_open_pdf(self):
        # Keep Dialog for File Opening (Standard Standard)
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if path:
            self._current_pdf_path = Path(path)
            self._cache_dir = self._orchestrator.get_cache_dir_for_pdf(self._current_pdf_path)
            self._page_texts.clear()
            self._auto_mode = False
            
            self._set_status(f"Loaded: {self._current_pdf_path.name}")
            self.setWindowTitle(f"AuraLens - {self._current_pdf_path.name}")
            
            if self._orchestrator.is_fully_cached(self._cache_dir):
                self._dashboard_page.set_current_file(self._current_pdf_path, "Ready")
            else:
                self._dashboard_page.set_current_file(self._current_pdf_path, "New")

    # ── Status bar ──────────────────────────────────────────────────
    def _setup_status_bar(self) -> None:
        self._status_label = QLabel("Ready")
        self.statusBar().addPermanentWidget(self._status_label)

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    # ── Inbox (Unchanged) ──────────────────────────────────────────
    def _setup_inbox_monitor(self):
        self._inbox_monitor = InboxMonitor(parent=self)
        self._inbox_monitor.pdf_detected.connect(self._on_inbox_pdf_detected)
        if self._config.inbox_dir.strip(): self._inbox_monitor.start(self._config.inbox_dir)

    def _connect_inbox_signals(self):
        self._inbox_coordinator.status_updated.connect(self._set_status)
        self._inbox_coordinator.processing_requested.connect(self._on_inbox_processing_requested)

    def _on_inbox_pdf_detected(self, pdf_path):
        self._inbox_coordinator.queue_pdf(Path(str(pdf_path)))
        self._inbox_coordinator.process_next_if_ready(self._is_processing)

    def _on_inbox_processing_requested(self, pdf_path):
        self._auto_mode = True
        self._current_pdf_path = pdf_path
        self._page_texts.clear()
        self._start_extraction()

    # ── Processing & Workers (Copied Logic) ─────────────────────────
    # Keeping existing logic for extraction/OCR but adapting UI switches
    
    def _start_extraction(self):
        self._cache_dir = self._orchestrator.get_cache_dir_for_pdf(self._current_pdf_path)
        params = self._orchestrator.get_extraction_params()
        self._is_processing = True
        self._stack.setCurrentWidget(self._processing_widget)
        self._processing_widget.set_stage("Extracting Pages...")
        
        self._worker = ExtractionWorker(pdf_path=self._current_pdf_path, **params)
        self._worker.page_extracted.connect(lambda p, t: self._processing_widget.update_page(p, t))
        self._worker.extraction_finished.connect(self._on_extraction_finished)
        self._worker.start()

    def _on_extraction_finished(self, cache_dir, total):
        self._cache_dir = Path(cache_dir)
        self._worker = None
        
        if self._auto_mode:
            self._start_ocr(resume=True)
        else:
             # Load Split View
             page_paths = self._orchestrator.get_page_paths_from_cache(self._cache_dir)
             if not self._page_texts: self._page_texts = [""] * total
             self._process_page.load_pages(page_paths, self._page_texts)
             # Check if completed (e.g. from previous run) to show correct buttons
             is_complete = self._orchestrator.is_fully_cached(self._cache_dir)
             self._process_page.set_ocr_completed(is_complete)
             
             is_complete = self._orchestrator.is_fully_cached(self._cache_dir)
             self._process_page.set_ocr_completed(is_complete)
             
             self._stack.setCurrentWidget(self._process_page)

    def _load_from_cache(self):
        """Load fully processed PDF from cache into Split Processing View."""
        if not self._cache_dir: return

        page_paths = self._orchestrator.get_page_paths_from_cache(self._cache_dir)
        # Load text for all pages
        total = len(page_paths)
        from core.page_cache import load_page_text
        
        self._page_texts = []
        for i in range(1, total + 1):
            text = load_page_text(self._cache_dir, i)
            self._page_texts.append(text)

        self._process_page.load_pages(page_paths, self._page_texts)
        self._process_page.set_ocr_completed(True)
        self._stack.setCurrentWidget(self._process_page)
        self._set_status("Loaded from Cache")


    def _start_ocr(self, resume: bool = True):
        """Start or resume OCR processing."""
        if not self._cache_dir: return

        skip_pages = set()
        if resume:
            skip_pages = self._orchestrator.calculate_resume_pages(self._cache_dir)

        params = self._orchestrator.get_ocr_params()
        self._is_processing = True
        
        # Setup UI
        self._stack.setCurrentWidget(self._processing_widget)
        self._processing_widget.set_stage("Running OCR..." if not skip_pages else "Resuming OCR...")
        
        page_paths = self._orchestrator.get_page_paths_from_cache(self._cache_dir)
        total = len(page_paths)
        
        # If we have existing text, pre-fill it so we don't lose it
        # (OCRWorker does this now for skipped pages, but good to ensure state)
        if len(self._page_texts) != total:
             self._page_texts = [""] * total

        self._worker = OCRWorker(
            page_paths=page_paths,
            skip_pages=skip_pages,
            **params
        )
        self._worker.page_started.connect(lambda p, t: self._processing_widget.update_page(p, t))
        self._worker.page_completed.connect(self._on_page_ocr_completed)
        self._worker.processing_finished.connect(self._on_ocr_finished)
        self._worker.start()

    def _on_page_ocr_completed(self, page_num: int, total: int, text: str):
        self._processing_widget.update_page(page_num, total)
        # Update internal state and cache immediately
        if 0 <= page_num - 1 < len(self._page_texts):
            self._page_texts[page_num - 1] = text
        if 0 <= page_num - 1 < len(self._page_texts):
            self._page_texts[page_num - 1] = text
        save_page_text(self._cache_dir, page_num, text)

    def _on_save_page_text(self, page_num: int, text: str):
        """Manually save text for a specific page."""
        if not self._cache_dir: return
        
        save_page_text(self._cache_dir, page_num, text)
        if 0 <= page_num - 1 < len(self._page_texts):
             self._page_texts[page_num - 1] = text
        self._set_status(f"Saved Page {page_num}")

    def _on_ocr_finished(self):
        self._worker = None
        self._is_processing = False
        self._processing_widget.finish()
        
        # Load results into view
        page_paths = self._orchestrator.get_page_paths_from_cache(self._cache_dir)
        self._process_page.load_pages(page_paths, self._page_texts)
        self._process_page.set_ocr_completed(True) # Assuming success leads to complete state
        
        self._stack.setCurrentWidget(self._process_page)
        self._set_status("OCR Completed")

    def _on_accept_book(self):
        """Compile all pages and save to user-selected file."""
        if not self._page_texts:
            QMessageBox.warning(self, "Empty Book", "No text to save.")
            return

        # 1. Update with latest edits from UI
        self._page_texts = self._process_page.get_all_texts()
        
        # 2. Ask user for save location
        default_name = self._current_pdf_path.stem if self._current_pdf_path else "book"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Book", f"{default_name}.txt", _SAVE_FILTERS
        )
        
        if not path:
            return
            
        output_path = Path(path)
        assembler = BookAssembler()
        
        try:
            if output_path.suffix == ".txt":
                assembler.save_to_file(self._page_texts, output_path)
            elif output_path.suffix == ".md":
                assembler.save_as_markdown(self._page_texts, output_path)
            elif output_path.suffix == ".epub":
                assembler.save_as_epub(self._page_texts, output_path, title=default_name)
            
            QMessageBox.information(self, "Saved", f"Book saved to:\n{output_path}")
            self._set_status(f"Saved: {output_path.name}")
            
        except Exception as e:
            logger.error("Failed to save book: %s", e)
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")

    def _on_cancel_processing(self):
        if self._worker:
            self._worker.cancel()
        self._on_home()
        
    def _restore_window_geometry(self) -> None:
        from PySide6.QtWidgets import QApplication
        self.resize(self._config.window_width, self._config.window_height)
        screen = QApplication.primaryScreen().availableGeometry()
        x, y = self._config.window_x, self._config.window_y
        if x > 0 and y > 0:
            # Clamp to screen so window can't be placed fully off-screen
            x = min(x, screen.right() - self.width())
            y = min(y, screen.bottom() - self.height())
            self.move(max(screen.left(), x), max(screen.top(), y))
        else:
            # Centre on screen
            self.move(
                screen.center().x() - self.width() // 2,
                screen.center().y() - self.height() // 2,
            )

    def closeEvent(self, event):
        self._config.window_width = self.width()
        self._config.window_height = self.height()
        self._config.window_x = self.x()
        self._config.window_y = self.y()
        save_config(self._config)
        event.accept()
        
    # ── Re-scan Logic ────────────────────────────────────────────────

    def _on_re_scan_page(self, page_num: int) -> None:
        """Re-run OCR on a single page without leaving the split view."""
        if not self._cache_dir:
            return
        page_paths = self._orchestrator.get_page_paths_from_cache(self._cache_dir)
        if not (1 <= page_num <= len(page_paths)):
            return

        self._process_page.show_scanning()
        params = self._orchestrator.get_ocr_params()
        self._rescan_page_num = page_num
        self._rescan_token_count = 0
        self._rescan_max_tokens = params["max_tokens"]

        self._worker = VLMWorker(
            page_path=page_paths[page_num - 1],
            api_url=params["api_url"],
            api_key=params["api_key"],
            model_name=params["model_name"],
            timeout=params["timeout"],
            max_tokens=params["max_tokens"],
            temperature=params["temperature"],
            system_prompt=params["system_prompt"],
            user_prompt=params["user_prompt"],
        )
        self._worker.token_received.connect(self._on_rescan_token)
        self._worker.result_ready.connect(self._on_rescan_complete)
        self._worker.error_occurred.connect(self._on_rescan_error)
        self._worker.finished.connect(self._process_page.hide_scanning)
        self._worker.start()

    def _on_rescan_token(self, _chunk: str) -> None:
        """Advance rescan progress bar based on received token count."""
        self._rescan_token_count += 1
        pct = min(95, int(self._rescan_token_count * 100
                          / max(1, self._rescan_max_tokens)))
        self._process_page.set_rescan_progress(pct)

    def _on_rescan_complete(self, text: str) -> None:
        """Update split view with freshly scanned text."""
        self._process_page.update_page_text(self._rescan_page_num, text)

    def _on_rescan_error(self, msg: str) -> None:
        QMessageBox.warning(self, "Re-scan Error", f"Re-scan failed: {msg}")
