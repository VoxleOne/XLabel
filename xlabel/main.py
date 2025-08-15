import sys
from PySide6.QtWidgets import QApplication
from xlabel.xlabel_gui.main_window import XLabelMainWindow

def main():
    """
    Main entry point for the XLabel application.
    Initializes the QApplication and the main window.
    """
    # It's good practice to set the application name for display purposes
    QApplication.setApplicationName("XLabel")
    QApplication.setOrganizationName("XLabel")

    app = QApplication(sys.argv)
    
    # All imports are now absolute from the 'xlabel' package
    win = XLabelMainWindow()
    win.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
