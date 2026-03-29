import pytest
from PySide6.QtWidgets import QApplication
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frm_Main import MainWindow
from unittest.mock import Mock

@pytest.fixture(scope="session")
def app(qtbot):
    """Fixture to create a Qt application instance."""
    app = QApplication(sys.argv)  # Pass sys.argv for proper command-line argument handling
    yield app
    app.quit() # Ensure the app is closed after tests

@pytest.fixture
def main_window(app, qtbot):
    window = MainWindow()
    window.show()

    # Simulate user input:
    qtbot.mouseClick(window.tableWidget.cellWidget(0, 0), QtCore.QPoint(10, 10)) # Example click on the input path widget
    # ... set other values in widgets...

    # Mock the ConversionWorker to avoid actual conversion
    mock_worker = Mock()
    window.worker = mock_worker

    # Simulate clicking the Launch button:
    qtbot.mouseClick(window.tableWidget.cellWidget(0, 3)) # Click on launch button

    # Assert that the worker's start method was called:
    mock_worker.start.assert_called()

    # Assert status bar message (example)
    # assert "Conversion started..." in window.statusBar().text()

    return window

