import socketserver
import webbrowser
import threading
import http.server
import os
import urllib.parse
import socket
import mmap
from modules.utils import get_local_ip, format_size, format_date
from config import PORT

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 50

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4194304)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        super().server_bind()

class USBFileHandler(http.server.SimpleHTTPRequestHandler):
    rbufsize = 2097152  # 2MB read buffer
    wbufsize = 2097152  # 2MB write buffer
    
    def __init__(self, *args, directory=None, port=None, **kwargs):
        self.base_path = os.path.abspath(directory) if directory else os.getcwd()
        self.port = port
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'public, max-age=31536000')
        self.send_header('X-Sendfile-Type', 'X-Sendfile')
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        
        if os.path.isfile(path):
            try:
                file_size = os.path.getsize(path)
                
                range_header = self.headers.get('Range')
                if range_header:
                    start, end = self.parse_range_header(range_header, file_size)
                    if start is not None and end is not None:
                        return self.serve_range(path, start, end, file_size)

                return self.serve_file(path, file_size)
                
            except Exception as e:
                self.send_error(500, f"Server error: {e}")
                return
        
        if os.path.isdir(path):
            self.list_directory(path)
        else:
            self.send_error(404, "File not found")

    def serve_file(self, path, file_size):
        try:
            with open(path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Content-Length', str(file_size))
                self.end_headers()
                
                if file_size > 1024 * 1024:  # Files larger than 1MB
                    self.transfer_large_file(f, file_size)
                else:
                    self.transfer_small_file(f)
                    
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")

    def transfer_large_file(self, f, file_size):
        try:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                chunk_size = 1024 * 1024 * 4  # 4MB chunks
                for i in range(0, len(mm), chunk_size):
                    chunk = mm[i:min(i + chunk_size, len(mm))]
                    self.wfile.write(chunk)
        except Exception:
            self.transfer_small_file(f)

    def transfer_small_file(self, f):
        chunk_size = 262144  # 256KB chunks
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            try:
                self.wfile.write(chunk)
            except (ConnectionResetError, BrokenPipeError):
                break

    def parse_range_header(self, range_header, file_size):
        try:
            range_value = range_header.split('=')[1]
            start, end = range_value.split('-')
            start = int(start) if start else 0
            end = int(end) if end else file_size - 1
            return start, end
        except:
            return None, None

    def serve_range(self, path, start, end, file_size):
        length = end - start + 1
        
        try:
            with open(path, 'rb') as f:
                f.seek(start)
                self.send_response(206)
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Content-Length', str(length))
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.end_headers()
                
                remaining = length
                chunk_size = min(262144, length)  # 256KB or smaller
                
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
                    except (ConnectionResetError, BrokenPipeError):
                        break
                        
        except Exception as e:
            self.send_error(500, f"Error serving range: {e}")

    def translate_path(self, path):
        path = urllib.parse.unquote(path.split('?', 1)[0].split('#', 1)[0])
        path = path.strip('/')
        words = path.split('/')
        words = filter(None, words)
        path = self.base_path
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path

    def list_directory(self, path):
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None
        
        list.sort(key=lambda x: x.lower())
        
        r = []
        r.append('<!DOCTYPE HTML>')
        r.append('<html>\n<head>')
        r.append('<meta charset="utf-8">')
        r.append('<title>USB File Sharing</title>')
        r.append('''
        <style>
            body { 
                font-family: Ubuntu, Arial, sans-serif; 
                margin: 20px; 
                background-color: #f5f5f5; 
            }
            
            h2 { 
                color: #333; 
                margin-bottom: 20px;
            }
            
            .container { 
                max-width: 1000px; 
                margin: 0 auto; 
                padding: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .file-list { 
                list-style-type: none; 
                padding: 0; 
            }
            
            .file-item { 
                display: flex;
                align-items: center;
                padding: 12px 15px;
                margin: 8px 0;
                background-color: #f8f9fa;
                border-radius: 6px;
                transition: background-color 0.2s;
            }
            
            .file-item:hover {
                background-color: #e9ecef;
            }
            
            .file-link { 
                color: #0066cc; 
                text-decoration: none; 
                flex-grow: 1;
                font-size: 15px;
            }
            
            .file-info { 
                color: #666; 
                font-size: 14px; 
                margin-left: 15px;
                white-space: nowrap;
            }
            
            .folder-icon::before {
                content: "📁";
                margin-right: 8px;
                font-size: 16px;
            }
            
            .file-icon::before {
                content: "📄";
                margin-right: 8px;
                font-size: 16px;
            }

            .zip-icon::before {
                content: "🗜️";
                margin-right: 8px;
                font-size: 16px;
            }
            
            .path-info {
                color: #666;
                font-size: 14px;
                margin-bottom: 15px;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 4px;
            }
            
            .server-info {
                margin-top: 20px;
                padding: 10px;
                background-color: #e9ecef;
                border-radius: 4px;
                font-size: 13px;
                color: #666;
            }
        </style>
        ''')
        r.append('</head>')
        r.append('<body>')
        r.append('<div class="container">')
        
        rel_path = os.path.relpath(path, self.base_path)
        if rel_path == '.':
            display_path = 'USB Drive Root'
        else:
            display_path = rel_path
        r.append(f'<h2>Files in {display_path}</h2>')
        
        r.append('<div class="path-info">')
        r.append(f'Current location: {display_path}')
        r.append('</div>')
        
        r.append('<ul class="file-list">')
        
        if path != self.base_path:
            r.append('<li class="file-item">')
            r.append(f'<a href=".." class="file-link folder-icon">Parent Directory</a>')
            r.append('</li>')
        
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            
            try:
                stats = os.stat(fullname)
                size = format_size(stats.st_size)
                mtime = format_date(stats.st_mtime)
            except:
                size = "Unknown size"
                mtime = "Unknown date"
            
            is_dir = os.path.isdir(fullname)
            is_zip = name.lower().endswith('.zip')
            
            if is_dir:
                displayname = name + "/"
                linkname = name + "/"
                size = "Directory"
                icon_class = "folder-icon"
            elif is_zip:
                icon_class = "zip-icon"
            else:
                icon_class = "file-icon"
            
            r.append('<li class="file-item">')
            r.append(f'<a href="{urllib.parse.quote(linkname)}" class="file-link {icon_class}">{displayname}</a>')
            r.append(f'<span class="file-info">{size} • {mtime}</span>')
            r.append('</li>')
        
        r.append('</ul>')
        
        r.append('<div class="server-info">')
        r.append(f'Server Port: {self.port} • ')
        r.append(f'Files served from: {self.base_path}')
        r.append('</div>')
        
        r.append('</div>')
        r.append('</body>\n</html>\n')
        
        encoded = '\n'.join(r).encode('utf-8', 'replace')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None

class FileServer:
    def __init__(self, directory, port=PORT):
        self.directory = directory
        self.port = port
        self.httpd = None
        self.server_thread = None

    def start(self):
        handler = lambda *args, **kwargs: USBFileHandler(*args, directory=self.directory, port=self.port, **kwargs)
        
        try:
            self.httpd = ThreadedTCPServer(("", self.port), handler)
            
            local_ip = get_local_ip()
            print(f"\nServer for {self.directory} started!")
            print(f"Local access: http://localhost:{self.port}")
            print(f"Network access: http://{local_ip}:{self.port}")
            
            self.server_thread = threading.Thread(target=self.httpd.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            webbrowser.open(f"http://localhost:{self.port}")
            
        except Exception as e:
            print(f"Server error on port {self.port}: {e}")
            self.stop()

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
                print(f"\nServer on port {self.port} stopped.")
            except Exception as e:
                print(f"Error stopping server on port {self.port}: {e}")