# AuraLens

AuraLens is a modern, VLM-based desktop application for high-quality OCR and document digitization. It uses Vision Language Models (specifically Qwen2.5-VL via OpenWebUI) to process PDFs page-by-page, preserving layout, reading order, and typography far better than traditional OCR tools.

## Features

- **VLM-Powered OCR:** Uses state-of-the-art visual language models (e.g., Qwen2.5-VL) for near-perfect text extraction.
- **Side-by-Side Verification:** View the original PDF page alongside the extracted text for easy proofreading and editing.
- **Hybrid Workflow:** 
  - **Manual Mode:** Open a PDF, process pages, review, and save.
  - **Inbox Mode:** Watch a folder for new PDFs and automatically process them in the background.
- **Cross-Platform:** Built with PySide6 (Qt) for Windows and Linux.
- **Pure Python Core:** Logic is separated from the GUI, enabling potential headless/CLI usage.

---

## Installation

### Prerequisites

1.  **Python 3.11**
2.  **Poppler** (for PDF rendering):
    - **Windows:** Download from [github.com/oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases), extract, and add the `bin/` folder to your implementation `PATH`.
    - **Linux:** `sudo apt-get install poppler-utils`
3.  **OpenWebUI** (or compatible API):
    - You need a running instance of OpenWebUI (or an OpenAI-compatible API) hosting a VLM like `Qwen2.5-VL-7B-Instruct`.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/AuraLens.git
    cd AuraLens/execution
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## Configuration

Launch the application:
```bash
python main.py
```

Click **Settings** in the toolbar to configure:

| Setting | Description | Recommended / Example |
| :--- | :--- | :--- |
| **API URL** | Endpoint for chat completions | `http://localhost:3000/api/chat/completions` |
| **API Key** | Your OpenWebUI API key | `sk-xxxxxxxxxxxx` |
| **Model Name** | Exact model ID in OpenWebUI | `qwen2.5-vl-7b-instruct` |
| **PDF DPI** | Resolution for page extraction | `150` (Higher = slower but clearer) |
| **Max Pixels** | Downscaling limit for VLM | `1003520` (Default for Qwen2.5-VL) |
| **Inbox Dir** | Folder to watch for auto-processing (Supports Windows `C:\...` and Linux `/home/...` paths) | `C:\Users\You\Documents\AuraLens_Inbox` |
| **Outbox Dir** | Folder for saved text files (Supports Windows `C:\...` and Linux `/home/...` paths) | `C:\Users\You\Documents\AuraLens_Outbox` |

---

## Usage Guide

### Manual Workflow
1.  Click **Open PDF** and select a file.
2.  Click **Process**.
    - **Stage 1 (Extraction):** Converts PDF pages to images.
    - **Stage 2 (Review):** (Optional) Review generated images.
    - **Stage 3 (OCR):** Sends images to the VLM for text extraction.
3.  **Verify & Edit:**
    - Use the **Page Viewer** to navigate pages.
    - Edit text in the right-hand panel.
    - Zoom/Pan the image on the left (Ctrl+Scroll / Drag).
4.  Click **Save Book** to export the result (Text, Markdown, or EPUB).

### Inbox Workflow (Automated)
1.  Set an **Inbox Directory** in Settings.
2.  Drop a PDF file into that folder.
3.  AuraLens will automatically:
    - Detect the new file.
    - Queue it for processing.
    - Extract and OCR all pages (skipping manual review).
    - Save the result to the **Outbox Directory** (or the Inbox if not set).
4.  Track progress in the status bar (e.g., "Inbox: book.pdf queued (1 pending)").

---

## Testing

To run the test suite (requires `pytest`):

```bash
# From the project root (one level up from execution/)
python -m pytest tests/
```

## License
[Your License Here]
