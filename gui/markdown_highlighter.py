
import re
from typing import List, Tuple

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)


class MarkdownHighlighter(QSyntaxHighlighter):
    """Simple Markdown syntax highlighter for QPlainTextEdit."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self._setup_rules()

    def _setup_rules(self) -> None:
        """Define highlighting rules."""
        
        # 1. Headers (e.g., # Header)
        # Larger font, bold, blue-ish color
        header_fmt = QTextCharFormat()
        header_fmt.setFontWeight(QFont.Weight.Bold)
        header_fmt.setForeground(QColor("#4a90e2"))
        header_fmt.setFontPointSize(14) # Make headers slightly larger
        # Pattern: # followed by space and text
        self._rules.append((QRegularExpression(r"^#+ .+"), header_fmt))

        # 2. Bold (**text** or __text__)
        bold_fmt = QTextCharFormat()
        bold_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((QRegularExpression(r"\*\*.*?\*\*"), bold_fmt))
        self._rules.append((QRegularExpression(r"__.*?__"), bold_fmt))

        # 3. Italic (*text* or _text_)
        italic_fmt = QTextCharFormat()
        italic_fmt.setFontItalic(True)
        self._rules.append((QRegularExpression(r"\*.*?\*"), italic_fmt))
        self._rules.append((QRegularExpression(r"_.*?_"), italic_fmt))
        
        # 4. Monospace code (`code`)
        code_fmt = QTextCharFormat()
        code_fmt.setFontFamilies(["Consolas", "Monospace", "Courier New"])
        code_fmt.setForeground(QColor("#d63384")) # Pinkish for code
        self._rules.append((QRegularExpression(r"`[^`]+`"), code_fmt))

        # 5. Lists (- item or * item)
        list_fmt = QTextCharFormat()
        list_fmt.setForeground(QColor("#2c3e50"))
        list_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((QRegularExpression(r"^\s*[-*+] "), list_fmt))
        # Numbered lists
        self._rules.append((QRegularExpression(r"^\s*\d+\. "), list_fmt))

    def highlightBlock(self, text: str) -> None:
        """Apply highlighting rules to the block of text."""
        for pattern, fmt in self._rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
