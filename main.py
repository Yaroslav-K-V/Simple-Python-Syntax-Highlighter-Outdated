import sys
import asyncio
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from syntax_highlighter import Highlighter


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Python Syntax Highlighter")

        self.editor = QPlainTextEdit()
        self.highlighter = Highlighter(self.editor.document())

        self.load_button = QPushButton("Load")
        self.save_button = QPushButton("Save")
        self.load_button.clicked.connect(lambda: asyncio.run(self.load_file()))
        self.save_button.clicked.connect(lambda: asyncio.run(self.save_file()))

        buttons = QHBoxLayout()
        buttons.addWidget(self.load_button)
        buttons.addWidget(self.save_button)

        layout = QVBoxLayout()
        layout.addLayout(buttons)
        layout.addWidget(self.editor)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.resize(640, 480)

    async def load_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Python Files (*.py)",
        )
        if path:
            text = await asyncio.to_thread(self._read_file, path)
            self.editor.setPlainText(text)

    async def save_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "Python Files (*.py)",
        )
        if path:
            text = self.editor.toPlainText()
            await asyncio.to_thread(self._write_file, path, text)

    @staticmethod
    def _read_file(path: str) -> str:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    @staticmethod
    def _write_file(path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
