import sys
import os
import re
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog,
    QMessageBox, QTabWidget, QToolBar, QInputDialog, QLineEdit
)
from PySide6.QtGui import (
    QIcon, QKeySequence, QTextCursor, QTextCharFormat,
    QColor, QSyntaxHighlighter, QAction
)
from PySide6.QtCore import Qt, QTimer
import qt_material


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#ff79c6"))
        keywords = [
            "def", "class", "import", "from", "as", "return", "if", "else", "elif",
            "for", "while", "try", "except", "with", "in", "is", "not", "and", "or"
        ]
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlighting_rules.append((re.compile(pattern), keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#f1fa8c"))
        self.highlighting_rules.append((re.compile(r'"[^"]*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^']*'"), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6272a4"))
        self.highlighting_rules.append((re.compile(r'#.*'), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Супер Современный Редактор")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.search_term = ""
        self.last_cursor_pos = 0

        self.init_toolbar()
        self.new_tab()

        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.auto_save)
        self.autosave_timer.start(1000 * 60)

    def init_toolbar(self):
        toolbar = QToolBar("Основной тулбар")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new_action = QAction(QIcon.fromTheme("document-new"), "Новый", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_tab)
        toolbar.addAction(new_action)

        open_action = QAction(QIcon.fromTheme("document-open"), "Открыть", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        save_action = QAction(QIcon.fromTheme("document-save"), "Сохранить", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        find_action = QAction(QIcon.fromTheme("edit-find"), "Найти", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self.find_text)
        toolbar.addAction(find_action)

        find_next_action = QAction("Найти далее", self)
        find_next_action.setShortcut(Qt.Key_F3)
        find_next_action.triggered.connect(self.find_next)
        toolbar.addAction(find_next_action)

        replace_action = QAction("Заменить", self)
        replace_action.setShortcut(QKeySequence.Replace)
        replace_action.triggered.connect(self.replace_text)
        toolbar.addAction(replace_action)

        toolbar.addSeparator()

        undo_action = QAction(QIcon.fromTheme("edit-undo"), "Отмена", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo_text)
        toolbar.addAction(undo_action)

        redo_action = QAction(QIcon.fromTheme("edit-redo"), "Повторить", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.redo_text)
        toolbar.addAction(redo_action)

    def new_tab(self):
        editor = QTextEdit()
        editor.textChanged.connect(self.set_tab_modified)
        editor.textChanged.connect(self.on_text_changed)  # ← добавлено
        index = self.tabs.addTab(editor, "Новый документ")
        self.tabs.setCurrentIndex(index)

    def current_editor(self):
        return self.tabs.currentWidget()

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Все файлы (*.*)")
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                text = f.read()
            editor = QTextEdit()
            editor.setPlainText(text)
            editor.textChanged.connect(self.set_tab_modified)
            editor.textChanged.connect(self.on_text_changed)  # ← добавлено
            if filename.endswith((".py", ".md", ".html")):
                SyntaxHighlighter(editor.document())
            index = self.tabs.addTab(editor, os.path.basename(filename))
            editor.file_path = filename
            self.tabs.setCurrentIndex(index)

    def save_file(self):
        editor = self.current_editor()
        if editor:
            path = getattr(editor, 'file_path', None)
            if not path:
                path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", "Текстовые файлы (*.txt)")
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
                editor.file_path = path
                self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(path))
                editor.document().setModified(False)

    def find_text(self):
        editor = self.current_editor()
        if editor:
            find_str, ok = QInputDialog.getText(self, "Поиск", "Что найти:")
            if ok and find_str:
                self.search_term = find_str
                self.last_cursor_pos = 0
                self.clear_highlight(editor)
                self.highlight_all(editor, find_str)

    def find_next(self):
        editor = self.current_editor()
        if editor and self.search_term:
            document = editor.document()
            cursor = editor.textCursor()
            cursor.setPosition(self.last_cursor_pos)
            found = document.find(self.search_term, cursor)
            if found.isNull():
                cursor.setPosition(0)
                found = document.find(self.search_term, cursor)
            if not found.isNull():
                editor.setTextCursor(found)
                self.last_cursor_pos = found.position()

    def replace_text(self):
        editor = self.current_editor()
        if editor:
            find_str, ok1 = QInputDialog.getText(self, "Заменить", "Что найти:")
            if ok1 and find_str:
                replace_str, ok2 = QInputDialog.getText(self, "Заменить на", "Заменить на что:")
                if ok2:
                    text = editor.toPlainText()
                    new_text = text.replace(find_str, replace_str)
                    editor.setPlainText(new_text)

    def highlight_all(self, editor, text):
        cursor = editor.textCursor()
        cursor.beginEditBlock()

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#ffeb3b"))

        regex = re.compile(re.escape(text), re.IGNORECASE)
        document_text = editor.toPlainText()

        first_found_cursor = None

        for match in regex.finditer(document_text):
            start, end = match.span()

            temp_cursor = editor.textCursor()
            temp_cursor.setPosition(start)
            temp_cursor.setPosition(end, QTextCursor.KeepAnchor)
            temp_cursor.mergeCharFormat(fmt)

            if first_found_cursor is None:
                first_found_cursor = temp_cursor

        cursor.endEditBlock()

        if first_found_cursor:
            editor.setTextCursor(first_found_cursor)
        else:
            QMessageBox.information(self, "Поиск", "Текст не найден.")

    def clear_highlight(self, editor):
        cursor = editor.textCursor()
        cursor.beginEditBlock()

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(Qt.transparent))

        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.mergeCharFormat(fmt)

        cursor.endEditBlock()

    def undo_text(self):
        editor = self.current_editor()
        if editor:
            editor.undo()

    def redo_text(self):
        editor = self.current_editor()
        if editor:
            editor.redo()

    def set_tab_modified(self):
        editor = self.current_editor()
        if editor and editor.document().isModified():
            current_text = self.tabs.tabText(self.tabs.currentIndex())
            if not current_text.endswith('*'):
                self.tabs.setTabText(self.tabs.currentIndex(), current_text + '*')

    def on_text_changed(self):
        editor = self.current_editor()
        if editor:
            # Мы не очищаем подсветку каждый раз, только при действии поиска
            pass

    def auto_save(self):
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if hasattr(editor, 'file_path') and editor.document().isModified():
                with open(editor.file_path, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
                editor.document().setModified(False)
                if self.tabs.tabText(i).endswith('*'):
                    self.tabs.setTabText(i, self.tabs.tabText(i)[:-1])

    def closeEvent(self, event):
        unsaved = any(self.tabs.widget(i).document().isModified() for i in range(self.tabs.count()))
        if unsaved:
            reply = QMessageBox.question(self, "Выход", "Есть несохранённые изменения. Сохранить перед выходом?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                self.save_file()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Тема Material Dark
    qt_material.apply_stylesheet(app, theme='dark_cyan.xml')

    window = TextEditor()
    window.show()
    sys.exit(app.exec())