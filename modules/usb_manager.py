# modules/usb_manager.py

import subprocess
import os
import tempfile
from config import DEFAULT_MOUNT_PREFIX

class USBManager:
    @staticmethod
    def check_ntfs_support():
        try:
            subprocess.run(['which', 'ntfs-3g'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def install_ntfs_support():
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ntfs-3g'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def get_usb_drives():
        """Get list of USB and external drives"""
        drives = []
        try:
            # Get all block devices with detailed info
            cmd = "lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINT,LABEL,TYPE,TRAN -n"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8')
            
            # Get additional USB information
            usb_devices = set()
            try:
                usb_cmd = "find /sys/devices -name removable | grep usb"
                usb_result = subprocess.check_output(usb_cmd, shell=True).decode('utf-8')
                for path in usb_result.splitlines():
                    try:
                        with open(path) as f:
                            if f.read().strip() == '1':
                                device_path = os.path.dirname(path)
                                for block in os.listdir(device_path):
                                    if block.startswith('sd'):
                                        usb_devices.add(block[:3])
                    except:
                        continue
            except:
                pass

            # Process each line from lsblk output
            for line in result.splitlines():
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) >= 3:
                    device_name = parts[0].replace('├─', '').replace('└─', '')
                    device_type = parts[5] if len(parts) > 5 else ""
                    transport = parts[6] if len(parts) > 6 else ""
                    
                    # Check if it's a partition
                    if device_type == "part":
                        is_usb = False
                        base_device = device_name.rstrip('0123456789')
                        
                        # Check multiple conditions for USB/external drives
                        if (
                            # Check if it's in our USB devices list
                            base_device in usb_devices or
                            # Check transport type
                            transport in ['usb', 'sata'] or
                            # Check removable flag
                            os.path.exists(f"/sys/block/{base_device}/removable")
                        ):
                            try:
                                # Check removable flag
                                with open(f"/sys/block/{base_device}/removable") as f:
                                    if f.read().strip() == '1':
                                        is_usb = True
                            except:
                                # If we can't read removable flag but other conditions met
                                if transport in ['usb', 'sata']:
                                    is_usb = True
                        
                        if is_usb:
                            drives.append((device_name, line))

            # If no drives found, try alternative method
            if not drives:
                cmd = "find /dev/disk/by-id -type l -ls | grep usb"
                try:
                    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
                    for line in result.splitlines():
                        if 'part' in line:
                            device_path = os.path.realpath(line.split()[-1])
                            device_name = device_path.split('/')[-1]
                            # Get device info using lsblk
                            cmd = f"lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINT,LABEL,TYPE -n /dev/{device_name}"
                            dev_info = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
                            if dev_info:
                                drives.append((device_name, dev_info))
                except:
                    pass

        except Exception as e:
            print(f"Error detecting drives: {e}")
        
        return drives

    @staticmethod
    def get_mount_point(device_name):
        try:
            cmd = f"lsblk -n -o MOUNTPOINT /dev/{device_name}"
            mount_point = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if mount_point:
                return mount_point
        except:
            pass
        return None

    @staticmethod
    def mount_drive(device_name):
        # Check if already mounted
        existing_mount = USBManager.get_mount_point(device_name)
        if existing_mount:
            print(f"Using existing mount point: {existing_mount}")
            return existing_mount

        try:
            # Create mount point
            mount_point = tempfile.mkdtemp(prefix=DEFAULT_MOUNT_PREFIX)

            # Get filesystem type
            cmd = f"lsblk -n -o FSTYPE /dev/{device_name}"
            fs_type = subprocess.check_output(cmd, shell=True).decode().strip().lower()
            print(f"Detected filesystem: {fs_type}")

            # Mount command based on filesystem type
            if fs_type == 'ntfs':
                cmd = f"sudo mount -t ntfs-3g -o permissions,big_writes,uid={os.getuid()},gid={os.getgid()} /dev/{device_name} {mount_point}"
            elif fs_type in ['vfat', 'fat32', 'fat']:
                cmd = f"sudo mount -t vfat -o uid={os.getuid()},gid={os.getgid()},dmask=027,fmask=137 /dev/{device_name} {mount_point}"
            elif fs_type == 'exfat':
                cmd = f"sudo mount -t exfat /dev/{device_name} {mount_point}"
            else:
                cmd = f"sudo mount /dev/{device_name} {mount_point}"

            print(f"Mounting /dev/{device_name} ({fs_type}) to {mount_point}")
            subprocess.run(cmd, shell=True, check=True)

            return mount_point
        except subprocess.CalledProcessError as e:
            print(f"Error mounting drive: {e}")
            try:
                os.rmdir(mount_point)
            except:
                pass
            return None


    @staticmethod
    def unmount_drive(mount_point):
        if mount_point and mount_point.startswith(DEFAULT_MOUNT_PREFIX):
            try:
                subprocess.run(['sudo', 'umount', mount_point], check=True)
                os.rmdir(mount_point)
                return True
            except:
                pass
        return False