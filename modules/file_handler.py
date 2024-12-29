# modules/file_handler.py

import http.server
import os
import urllib.parse
from modules.utils import format_size, format_date, load_css

# modules/file_handler.py

import http.server
import os
import urllib.parse
from modules.utils import format_size, format_date

class USBFileHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        self.base_path = os.path.abspath(directory) if directory else os.getcwd()
        # Extract custom arguments to prevent passing them to super().__init__()
        self.port = kwargs.pop('port', None)
        # Unbuffer the input and output for improved performance
        self.rbufsize = 0
        self.wbufsize = 0
        super().__init__(*args, **kwargs)
        # Unbuffer the output
        self.wfile = self.connection.makefile('wb', buffering=0)

    def translate_path(self, path):
        """Translate URL path to filesystem path"""
        # Parse path with urllib
        path = urllib.parse.unquote(path.split('?', 1)[0].split('#', 1)[0])
        path = path.strip('/')
        words = path.split('/')
        words = filter(None, words)
        
        # Start from base path
        path = self.base_path
        
        # Add remaining path components
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Directory traversal attempt - ignore
                continue
            path = os.path.join(path, word)
        
        return path

    def list_directory(self, path):
        """Create the directory listing page"""
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
        r.append(f'<style>{load_css()}</style>')
        r.append('</head>')
        r.append('<body>')
        r.append('<div class="container">')
        
        # Show current path
        rel_path = os.path.relpath(path, self.base_path)
        if rel_path == '.':
            display_path = 'USB Drive Root'
        else:
            display_path = rel_path
        r.append(f'<h2>Files in {display_path}</h2>')
        
        r.append('<ul class="file-list">')
        
        # Add parent directory link if not in root
        if path != self.base_path:
            r.append('<li class="file-item">')
            r.append(f'<a href=".." class="file-link folder-icon">..</a>')
            r.append('</li>')
        
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            
            # Get file info
            try:
                stats = os.stat(fullname)
                size = format_size(stats.st_size)
                mtime = format_date(stats.st_mtime)
            except:
                size = "Unknown size"
                mtime = "Unknown date"
            
            is_dir = os.path.isdir(fullname)
            if is_dir:
                displayname = name + "/"
                linkname = name + "/"
                size = "Directory"
            
            r.append('<li class="file-item">')
            icon_class = "folder-icon" if is_dir else "file-icon"
            r.append(f'<a href="{urllib.parse.quote(linkname)}" class="file-link {icon_class}">{displayname}</a>')
            r.append(f'<span class="file-info">{size} - {mtime}</span>')
            r.append('</li>')
        
        r.append('</ul>')
        r.append('</div>')
        r.append('</body>\n</html>\n')
        
        encoded = '\n'.join(r).encode('utf-8', 'replace')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None