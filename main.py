# main.py

from modules.usb_manager import USBManager
from modules.server import FileServer
import os
import time
import threading
from config import PORT, MAX_SERVERS, DEFAULT_MOUNT_PREFIX  # Changed BASE_PORT to PORT

class USBFileSharing:
    def __init__(self):
        self.servers = []
        self.active_mounts = []

    def start_server(self, mount_point, port):
        server = FileServer(mount_point, port)
        server.start()
        return server

    def cleanup(self):
        print("\nCleaning up...")
        # Stop all servers
        for server in self.servers:
            server.stop()
        
        # Unmount all drives
        for mount_point in self.active_mounts:
            if mount_point.startswith(DEFAULT_MOUNT_PREFIX):
                USBManager.unmount_drive(mount_point)

    def run(self):
        print("USB File Sharing Server")
        print("======================")
        print(f"You can share up to {MAX_SERVERS} drives simultaneously")
        
        # Check for NTFS support
        if not USBManager.check_ntfs_support():
            print("NTFS support not found. Installing...")
            if not USBManager.install_ntfs_support():
                print("Failed to install NTFS support. Please install ntfs-3g manually.")
                return

        try:
            while True:
                # Get available drives
                drives = USBManager.get_usb_drives()
                if not drives:
                    print("\nNo USB drives detected!")
                    print("Make sure your USB drive is properly connected and has valid partitions.")
                    break

                # Show available drives
                print("\nAvailable USB drives and partitions:")
                for i, (_, drive_info) in enumerate(drives, 1):
                    print(f"{i}. {drive_info}")

                if len(self.servers) >= MAX_SERVERS:
                    print(f"\nMaximum number of servers ({MAX_SERVERS}) reached!")
                    print("Stop the program to reset or use existing servers.")
                    break

                # Get user choice
                try:
                    choice = input("\nSelect USB drive number (or 'q' to quit): ")
                    if choice.lower() == 'q':
                        break

                    choice = int(choice) - 1
                    if not (0 <= choice < len(drives)):
                        print("Invalid selection!")
                        continue

                    # Get device name from selection
                    device_name, _ = drives[choice]
                    print(f"\nSelected partition: {device_name}")

                    # Get mount point (existing or new)
                    mount_point = USBManager.mount_drive(device_name)
                    if not mount_point:
                        print("Failed to mount drive!")
                        continue

                    print(f"Using mount point: {mount_point}")
                    self.active_mounts.append(mount_point)

                    # Start the server with incremented port
                    port = PORT + len(self.servers)  # Changed from BASE_PORT to PORT
                    server = self.start_server(mount_point, port)
                    self.servers.append(server)

                    print(f"\nCurrently sharing {len(self.servers)} drive(s)")
                    print("Press Enter to share another drive or 'q' to quit")

                except ValueError:
                    print("Invalid input! Please enter a number.")

                if len(self.servers) >= MAX_SERVERS:
                    print(f"\nMaximum number of servers ({MAX_SERVERS}) reached!")
                    break

            # Wait for user to quit
            print("\nServers are running. Press Ctrl+C to stop all servers.")
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()

if __name__ == "__main__":
    sharing = USBFileSharing()
    sharing.run()