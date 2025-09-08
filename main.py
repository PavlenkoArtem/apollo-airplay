import sys
import time
import subprocess
import threading
import os
import psutil  # For process management
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPalette, QBrush

UXPLAY_SCRIPT = "/home/apollo/airplay.sh"  # Path to startup script
UXPLAY_BIN = "/usr/local/bin/uxplay"  # Main UxPlay binary file
BACKGROUND_IMAGE = "/home/apollo/airplay_gui/test_table_2.jpg"  # Background image
LOG_FILE = "uxplay.log"  # Log file
current_process = None  # Store UxPlay process


class PinWindow(QWidget):
    """Graphical window for displaying PIN code"""
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        """Setup interface"""
        self.setWindowTitle("Enter PIN")
        self.setGeometry(0, 0, 1920, 1080)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.showFullScreen()
        self.set_background(BACKGROUND_IMAGE)

        # Main layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Top layout with close button
        self.top_layout = QHBoxLayout()
        self.top_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.close_button = QPushButton("Close")
        self.close_button.setStyleSheet(
            "font-size: 20px; font-weight: bold; padding: 10px; background-color: red; color: white; border-radius: 10px;"
        )
        self.close_button.clicked.connect(self.close_app)
        self.top_layout.addWidget(self.close_button)

        # PIN code label
        self.label = QLabel("Waiting for PIN code...", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 60px; font-weight: bold; background-color: white; padding: 20px; border-radius: 10px;")
        self.setCursor(Qt.CursorShape.BlankCursor)

        # Add elements to main layout
        self.layout.addLayout(self.top_layout)  # Add close button
        self.layout.addStretch()  # Spacer
        self.layout.addWidget(self.label)  # PIN code text
        self.layout.addStretch()  # Spacer
        self.setLayout(self.layout)

    def close_app(self):
        """Closes application and kills background processes"""
        print("Closing window and terminating processes...")
        kill_uxplay_processes()  # Terminate all processes
        QApplication.instance().quit()

    def set_background(self, image_path):
        """Sets background image"""
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"Failed to load background image: {image_path}")
            return

        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window,
                         QBrush(pixmap.scaled(self.size(), Qt.AspectRatioMode.IgnoreAspectRatio)))
        self.setPalette(palette)

    def resizeEvent(self, event):
        """Redraw background when window size changes"""
        self.set_background(BACKGROUND_IMAGE)
        super().resizeEvent(event)

    def show_pin(self, pin):
        """Display PIN code in fullscreen"""
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.label.setText(f"PIN: {pin}")
        self.showFullScreen()

    def hide_window(self):
        """Hide window"""
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.hide()



def start_uxplay():
    """Start UxPlay via `airplay.sh`"""
    global current_process

    print("Starting UxPlay...")

    process = subprocess.Popen(
        ["stdbuf", "-oL", "sh", UXPLAY_SCRIPT],  # Disable stdout buffering
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    current_process = process  # Save process
    threading.Thread(target=follow_console_output, args=(process,), daemon=True).start()


def follow_console_output(process):
    """Read real-time stdout and stderr from UxPlay"""
    global pin_window

    with open(LOG_FILE, "a") as log_file:  # Open log file only once
        while True:
            line = process.stdout.readline()
            if line == "" and process.poll() is not None:  # If process ended
                print("UxPlay terminated! Restarting...")
                start_uxplay()  # Restart
                break

            if line:
                line = line.strip()
                log_file.write(line + "\n")  # Write to file
                log_file.flush()  # Force write to file

                # If server started successfully
                if "Initialized server socket(s)" in line:
                    print("Server initialized! Ready for connections.")

                elif "CLIENT MUST NOW ENTER PIN =" in line:
                    pin = line.split('"')[1]
                    print(f"{line}")
                    pin_window.show_pin(pin)  # Display PIN on screen

                elif "Accepted IPv6 client on socket" in line:
                    print(f"{line}")
                    pin_window.hide_window()  # Hide PIN code on connection

                elif "Connection request from" in line:
                    print(f"{line}")
                    pin_window.hide_window()  # Hide PIN code on connection

                elif "Connection closed for socket" in line:
                    print(f"{line}")
                    pin_window.showFullScreen()  # Show window again on connection loss


def kill_uxplay_processes():
    """Kills all active UxPlay and startup script processes"""
    for process in psutil.process_iter(attrs=["pid", "cmdline"]):
        try:
            cmdline = " ".join(process.info["cmdline"]) if process.info["cmdline"] else ""

            if UXPLAY_SCRIPT in cmdline or UXPLAY_BIN in cmdline:
                print(f"Terminating process PID {process.info['pid']}: {cmdline}")
                process.terminate()  # Send SIGTERM

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


if __name__ == "__main__":
    print("Checking existing UxPlay processes...")

    # Close old UxPlay processes before startup
    kill_uxplay_processes()
    time.sleep(1)  # Give 1 second for termination

    print("Starting UxPlay and GUI...")

    app = QApplication(sys.argv)
    pin_window = PinWindow()
    start_uxplay()

    sys.exit(app.exec())
