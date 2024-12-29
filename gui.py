from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QFileDialog, QListWidget,
                            QGroupBox, QTextEdit, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QFont
import os
from datetime import datetime
from modules.server import FileServer
from modules.utils import format_size, get_local_ip

class ServerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('File Server Control Panel')
        self.setMinimumSize(800, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Directory Selection
        dir_group = QGroupBox("Directory Selection")
        dir_layout = QHBoxLayout()
        
        self.dir_label = QLabel("No directory selected")
        self.dir_label.setStyleSheet("padding: 5px; background: #f0f0f0; border-radius: 3px;")
        dir_layout.addWidget(self.dir_label)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_btn)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # Server Control
        control_group = QGroupBox("Server Control")
        control_layout = QHBoxLayout()
        
        self.status_label = QLabel("Server Status: Stopped")
        self.status_label.setStyleSheet("color: red;")
        control_layout.addWidget(self.status_label)
        
        self.toggle_btn = QPushButton("Start Server")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.toggle_server)
        control_layout.addWidget(self.toggle_btn)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Server Info
        info_group = QGroupBox("Server Information")
        info_layout = QVBoxLayout()
        
        self.server_info = QTextEdit()
        self.server_info.setReadOnly(True)
        info_layout.addWidget(self.server_info)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Network Info
        network_group = QGroupBox("Network Information")
        network_layout = QVBoxLayout()
        
        self.local_ip = get_local_ip()
        self.network_info = QLabel(f"Local IP: {self.local_ip}")
        network_layout.addWidget(self.network_info)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        self.apply_styles()
        self.show()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 3px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:checked {
                background-color: #cc0000;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
                font-family: monospace;
            }
            QLabel {
                color: #333333;
            }
            .status-running {
                color: green;
                font-weight: bold;
            }
            .status-stopped {
                color: red;
                font-weight: bold;
            }
        """)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Directory",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if dir_path:
            self.dir_label.setText(dir_path)
            self.log_info(f"Selected directory: {dir_path}")
    
    def toggle_server(self):
        if self.toggle_btn.isChecked():
            if not self.dir_label.text() or self.dir_label.text() == "No directory selected":
                self.log_info("Please select a directory first!")
                self.toggle_btn.setChecked(False)
                return
                
            self.start_server()
            self.toggle_btn.setText("Stop Server")
            self.status_label.setText("Server Status: Running")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.stop_server()
            self.toggle_btn.setText("Start Server")
            self.status_label.setText("Server Status: Stopped")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def start_server(self):
        try:
            self.server = FileServer(self.dir_label.text())
            self.server.start()
            self.log_info("Server started successfully!")
            self.log_info(f"Local access: http://localhost:{self.server.port}")
            self.log_info(f"Network access: http://{self.local_ip}:{self.server.port}")
            self.log_info("Optimized for high-speed file transfers")
            self.log_info("Ready to serve files...")
        except Exception as e:
            self.log_info(f"Error starting server: {str(e)}")
            self.toggle_btn.setChecked(False)
            self.toggle_btn.setText("Start Server")
    
    def stop_server(self):
        if self.server:
            self.server.stop()
            self.server = None
            self.log_info("Server stopped")
    
    def log_info(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.server_info.append(f"[{timestamp}] {message}")
    
    def closeEvent(self, event):
        self.stop_server()
        event.accept()

def main():
    import sys
    app = QApplication(sys.argv)
    ex = ServerGUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()