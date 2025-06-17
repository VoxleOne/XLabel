import sys
from PySide6.QtWidgets import QApplication
from .main_window import XLabelMainWindow

def main():
    app = QApplication(sys.argv)
    win = XLabelMainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()