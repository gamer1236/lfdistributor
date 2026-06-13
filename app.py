import os
import io
import json
import socket
import math
import time
import secrets
import threading
import ctypes
import sys
from collections import defaultdict
from flask import Flask, render_template, jsonify, request, send_file, Response, make_response

# Detect if running in a PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = os.path.dirname(sys.executable)
    # Flask templates and static folder are inside the bundle
    bundle_dir = sys._MEIPASS
    template_folder = os.path.join(bundle_dir, 'templates')
    static_folder = os.path.join(bundle_dir, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    # Running in normal python environment
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__)

# Constants and Directories
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
DEFAULT_SHARED_DIR = os.path.abspath(os.path.join(BASE_DIR, 'shared'))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

# Ensure essential directories exist
for directory in [CONFIG_DIR, DEFAULT_SHARED_DIR, LOGS_DIR, ASSETS_DIR]:
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except Exception as e:
            # Print to console before stdout redirection
            print(f"Error creating directory {directory}: {e}")

# Thread-safe logging to file and console
class Logger(object):
    def __init__(self, filename="server.log"):
        self.terminal = sys.stdout
        log_path = os.path.join(LOGS_DIR, filename)
        try:
            self.log = open(log_path, "a", encoding="utf-8")
        except Exception:
            self.log = None

    def write(self, message):
        if self.terminal:
            self.terminal.write(message)
        if self.log:
            try:
                self.log.write(message)
                self.log.flush()
            except Exception:
                pass

    def flush(self):
        if self.terminal:
            self.terminal.flush()
        if self.log:
            try:
                self.log.flush()
            except Exception:
                pass

sys.stdout = Logger("server.log")
sys.stderr = Logger("server.log")

# Resource integrity check
def check_resources():
    check_base = sys._MEIPASS if getattr(sys, 'frozen', False) else BASE_DIR
    required_files = [
        os.path.join(check_base, 'templates', 'index.html'),
        os.path.join(check_base, 'templates', 'host.html'),
        os.path.join(check_base, 'static', 'css', 'style.css'),
        os.path.join(check_base, 'static', 'js', 'app.js'),
        os.path.join(check_base, 'static', 'js', 'host.js')
    ]
    missing = []
    for f in required_files:
        if not os.path.exists(f):
            missing.append(os.path.relpath(f, check_base))
            
    if missing:
        error_msg = "The following required application files are missing:\n\n" + "\n".join(missing) + "\n\nPlease reinstall or repair the application."
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Local File Distributor - Error", 0x10) # 0x10 is MB_ICONERROR
        else:
            print(f"Error: {error_msg}")
        sys.exit(1)

check_resources()

# Thread-safe download counters
download_counters = defaultdict(int)
counters_lock = threading.Lock()

def increment_download(filepath):
    """Increments the in-memory download counter for a file path in a thread-safe manner."""
    with counters_lock:
        download_counters[filepath] += 1

def get_download_count(filepath):
    """Retrieves the in-memory download count for a file path."""
    with counters_lock:
        return download_counters[filepath]

def get_local_ip():
    """Detects and returns the active local IP address of the host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a non-existent external address (doesn't send packets)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def load_config():
    """Loads application configuration from config.json. Creates default config if missing."""
    default_config = {
        "shared_folder": DEFAULT_SHARED_DIR,
        "password_enabled": False,
        "password": "",
        "host_token": secrets.token_hex(16)
    }
    
    # Ensure default shared folder exists
    if not os.path.exists(DEFAULT_SHARED_DIR):
        try:
            os.makedirs(DEFAULT_SHARED_DIR)
        except Exception as e:
            print(f"Error creating default shared folder: {e}")
            
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
        return default_config
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Merge missing default configurations
        updated = False
        for k, v in default_config.items():
            if k not in config:
                config[k] = v
                updated = True
        
        # Normalize folder path to absolute
        if 'shared_folder' in config:
            abs_path = os.path.abspath(config['shared_folder'])
            if config['shared_folder'] != abs_path:
                config['shared_folder'] = abs_path
                updated = True
                
        if updated:
            save_config(config)
        return config
    except Exception as e:
        print(f"Error reading config, using defaults: {e}")
        return default_config

def save_config(config):
    """Saves application configuration to config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_safe_filepath(shared_folder, rel_path):
    """
    Validates the relative file path and returns its absolute path.
    Prevents directory traversal attacks by ensuring the target absolute path
    is strictly a child of the absolute shared folder path.
    """
    # Clean relative path to remove double slashes and resolve ..
    cleaned_rel_path = os.path.normpath(rel_path.lstrip('/\\'))
    if cleaned_rel_path == '.' or cleaned_rel_path == '':
        raise ValueError("Invalid path")
        
    abs_shared = os.path.realpath(shared_folder)
    target_abs = os.path.realpath(os.path.join(abs_shared, cleaned_rel_path))
    
    # Strict directory traversal check
    if not target_abs.startswith(abs_shared + os.sep) and target_abs != abs_shared:
        raise PermissionError("Directory traversal attempt detected")
        
    if not os.path.exists(target_abs):
        raise FileNotFoundError("File does not exist")
        
    if os.path.isdir(target_abs):
        raise ValueError("Requested resource is a directory, not a file")
        
    return target_abs

def get_unique_filename(directory, filename):
    """Generates a unique filename in the given directory by appending numbers if duplicates exist."""
    name, ext = os.path.splitext(filename)
    counter = 1
    unique_name = filename
    while os.path.exists(os.path.join(directory, unique_name)):
        unique_name = f"{name}_{counter}{ext}"
        counter += 1
    return unique_name

def format_size(size_bytes):
    """Helper to convert bytes into a human-readable size string."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def get_shared_files(shared_folder):
    """Scans the shared folder recursively and returns list of metadata for all files."""
    files_list = []
    if not os.path.exists(shared_folder) or not os.path.isdir(shared_folder):
        return files_list
        
    # Recursively traverse directory
    for root, dirs, files in os.walk(shared_folder):
        for file in files:
            abs_path = os.path.join(root, file)
            # Find path relative to the shared folder
            rel_path = os.path.relpath(abs_path, shared_folder).replace('\\', '/')
            try:
                stat = os.stat(abs_path)
                size_bytes = stat.st_size
                mtime = stat.st_mtime
                date_added = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
                files_list.append({
                    "name": file,
                    "rel_path": rel_path,
                    "size_bytes": size_bytes,
                    "size_str": format_size(size_bytes),
                    "mtime": mtime,
                    "date_added": date_added,
                    "download_count": get_download_count(rel_path)
                })
            except Exception as e:
                # Silently skip file if it cannot be accessed
                print(f"Error reading file {abs_path}: {e}")
    return files_list

# Authorization Helpers
def is_host():
    """
    Checks if the current request is from the Host.
    Authorized if accessing from localhost or if a valid host_token is provided.
    """
    config = load_config()
    token = request.args.get('token') or request.cookies.get('host_token') or request.headers.get('X-Host-Token')
    
    if token == config.get('host_token'):
        return True
    
    # Remote address checking for loopback
    if request.remote_addr in ('127.0.0.1', '::1'):
        return True
        
    return False

def is_client_authorized():
    """Checks if the client is authorized to access the system (or if no password is set)."""
    if is_host():
        return True
        
    config = load_config()
    if not config.get('password_enabled'):
        return True
        
    client_auth = request.cookies.get('client_auth')
    # If client cookie matches the plain text password
    return client_auth == config.get('password')

@app.route('/favicon.ico')
def favicon():
    """Serves an empty favicon to prevent browser console 404 errors."""
    return send_file(io.BytesIO(b""), mimetype='image/x-icon')

@app.route('/')
def index():
    """Renders the main client download dashboard page."""
    config = load_config()
    
    # Auto-save Host Token cookie if passed via URL parameter
    url_token = request.args.get('token')
    
    # Check if Host
    host_status = is_host()
    
    # Check if Client needs authentication
    auth_needed = not is_client_authorized()
    
    response = make_response(render_template('index.html', 
                                             is_host=host_status, 
                                             auth_needed=auth_needed,
                                             password_enabled=config.get('password_enabled')))
    
    # Store token in cookie if provided in query string to remember host session
    if url_token == config.get('host_token'):
        response.set_cookie('host_token', url_token, max_age=30*24*60*60, httponly=True)
        
    return response

@app.route('/host')
def host_page():
    """Renders the host administration portal. Redirects unauthorized clients."""
    if not is_host():
        # Render a simple template stating unauthorized or redirect
        return make_response(render_template('index.html',
                                             is_host=False,
                                             auth_needed=True,
                                             password_enabled=load_config().get('password_enabled'),
                                             unauthorized_error="Access Denied: Host administration only."), 403)
                                             
    config = load_config()
    return render_template('host.html',
                           is_host=True,
                           password_enabled=config.get('password_enabled'))

@app.route('/api/auth', methods=['POST'])
def authenticate():
    """Endpoint for clients to log in using the shared password."""
    config = load_config()
    if not config.get('password_enabled'):
        return jsonify({"success": True, "message": "No password required."})
        
    data = request.get_json() or {}
    password_attempt = data.get('password', '')
    
    if password_attempt == config.get('password'):
        resp = jsonify({"success": True, "message": "Authentication successful!"})
        resp.set_cookie('client_auth', password_attempt, max_age=7*24*60*60, httponly=True)
        return resp
    else:
        return jsonify({"success": False, "message": "Incorrect password. Please try again."}), 401

@app.route('/api/files')
def api_files():
    """Returns a list of all files currently available in the shared folder."""
    if not is_client_authorized():
        return jsonify({"error": "Unauthorized"}), 401
        
    config = load_config()
    shared_folder = config.get('shared_folder')
    
    # Rescan folders dynamically
    files_list = get_shared_files(shared_folder)
    
    # Calculate stats
    total_size = sum(f['size_bytes'] for f in files_list)
    
    return jsonify({
        "files": files_list,
        "count": len(files_list),
        "total_size_str": format_size(total_size)
    })

@app.route('/download/<path:rel_path>')
def download_file(rel_path):
    """Streams the requested file with support for chunking, range headers, and speed."""
    if not is_client_authorized():
        return jsonify({"error": "Unauthorized"}), 401
        
    config = load_config()
    shared_folder = config.get('shared_folder')
    
    try:
        abs_path = get_safe_filepath(shared_folder, rel_path)
        increment_download(rel_path)
        
        # conditional=True enables HTTP Range requests (crucial for resuming and streaming media)
        return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path), conditional=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except PermissionError:
        return jsonify({"error": "Access Denied (Traversal check failed)"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/qrcode')
def get_qrcode():
    """Generates and serves a local server connection URL QR Code as an SVG."""
    import qrcode
    import qrcode.image.svg
    
    ip = get_local_ip()
    port = request.environ.get('SERVER_PORT', '5000')
    url = f"http://{ip}:{port}"
    
    # Generate QR Code as SVG (Pure Python, no PIL required)
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(url, image_factory=factory)
    
    stream = io.BytesIO()
    img.save(stream)
    svg_xml = stream.getvalue()
    
    return Response(svg_xml, mimetype='image/svg+xml')

# --- HOST ADMIN API ---

@app.route('/api/host/upload', methods=['POST'])
def host_upload():
    """Saves uploaded files directly into the active shared folder. Streams chunk-by-chunk."""
    if not is_host():
        return jsonify({"error": "Unauthorized"}), 403
        
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
        
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({"error": "No files selected"}), 400
        
    config = load_config()
    shared_folder = config.get('shared_folder')
    
    if not os.path.exists(shared_folder) or not os.path.isdir(shared_folder):
        return jsonify({"error": "Active directory does not exist on disk"}), 500
        
    from werkzeug.utils import secure_filename
    
    success_uploads = []
    error_uploads = []
    
    for file in uploaded_files:
        orig_name = file.filename
        safe_name = secure_filename(orig_name)
        
        if not safe_name:
            safe_name = f"uploaded_{int(time.time())}"
            
        # Deduplicate names automatically
        unique_name = get_unique_filename(shared_folder, safe_name)
        target_path = os.path.join(shared_folder, unique_name)
        
        try:
            # Stream chunked write to disk (prevents loading complete files in RAM)
            with open(target_path, 'wb') as f:
                chunk_size = 8192
                while True:
                    chunk = file.stream.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
            success_uploads.append(unique_name)
        except Exception as e:
            error_uploads.append({"file": orig_name, "error": str(e)})
            
    if error_uploads and not success_uploads:
        return jsonify({"success": False, "message": "Failed to upload any files", "errors": error_uploads}), 500
        
    return jsonify({
        "success": True,
        "message": f"Successfully uploaded {len(success_uploads)} file(s).",
        "uploaded": success_uploads,
        "errors": error_uploads
    })

@app.route('/api/host/delete', methods=['POST'])
def host_delete():
    """Deletes a file from the shared directory. Requires host auth. Blocks directory traversal."""
    if not is_host():
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    rel_path = data.get('rel_path', '')
    
    if not rel_path:
        return jsonify({"error": "No file specified for deletion"}), 400
        
    config = load_config()
    shared_folder = config.get('shared_folder')
    
    try:
        abs_path = get_safe_filepath(shared_folder, rel_path)
        os.remove(abs_path)
        
        # Clean up download counts dictionary key
        with counters_lock:
            if rel_path in download_counters:
                del download_counters[rel_path]
                
        return jsonify({"success": True, "message": f"File '{os.path.basename(abs_path)}' has been deleted."})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except PermissionError:
        return jsonify({"error": "Unauthorized file location"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/host/config', methods=['GET', 'POST'])
def host_config():
    """API for viewing or updating the server settings. Host only."""
    if not is_host():
        return jsonify({"error": "Unauthorized"}), 403
        
    config = load_config()
    
    if request.method == 'GET':
        return jsonify({
            "shared_folder": config.get('shared_folder'),
            "password_enabled": config.get('password_enabled'),
            "password": config.get('password'),
            "local_ip": get_local_ip(),
            "server_url": f"http://{get_local_ip()}:5000",
            "host_token": config.get('host_token')
        })
        
    elif request.method == 'POST':
        data = request.get_json() or {}
        
        # Update shared folder
        new_folder = data.get('shared_folder')
        if new_folder:
            new_folder_abs = os.path.abspath(new_folder)
            if not os.path.exists(new_folder_abs) or not os.path.isdir(new_folder_abs):
                return jsonify({"success": False, "message": "Selected path is not a valid directory."}), 400
            config['shared_folder'] = new_folder_abs
            
        # Update password toggle
        if 'password_enabled' in data:
            config['password_enabled'] = bool(data.get('password_enabled'))
            
        # Update password
        if 'password' in data:
            pwd = data.get('password', '').strip()
            if config['password_enabled'] and not pwd:
                return jsonify({"success": False, "message": "Password cannot be empty when protection is enabled."}), 400
            config['password'] = pwd
            
        save_config(config)
        return jsonify({"success": True, "message": "Configuration updated successfully."})

@app.route('/api/host/browse')
def host_browse():
    """Allows the host to browse directories on their filesystem to select the shared folder. Host only."""
    if not is_host():
        return jsonify({"error": "Unauthorized"}), 403
        
    path = request.args.get('path', '').strip()
    
    # Handle root browsing
    if not path:
        # On Windows, list logical drives
        if os.name == 'nt':
            import string
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
            return jsonify({
                "current_path": "",
                "parent_path": "",
                "is_drives": True,
                "items": [{"name": d, "path": d, "is_dir": True} for d in drives]
            })
        else:
            path = '/'
            
    path = os.path.abspath(path)
    if not os.path.exists(path) or not os.path.isdir(path):
        return jsonify({"error": "Directory not found."}), 404
        
    try:
        items = []
        for name in os.listdir(path):
            item_path = os.path.join(path, name)
            try:
                if os.path.isdir(item_path):
                    items.append({
                        "name": name,
                        "path": item_path,
                        "is_dir": True
                    })
            except Exception:
                continue
                
        items.sort(key=lambda x: x['name'].lower())
        
        parent_path = os.path.dirname(path)
        if parent_path == path:
            parent_path = ""
            
        return jsonify({
            "current_path": path,
            "parent_path": parent_path,
            "is_drives": False,
            "items": items
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def open_browser():
    """Waits for Flask server to start and opens the default browser to the host page."""
    import webbrowser
    time.sleep(1.5)
    config = load_config()
    token = config.get('host_token')
    # Use 127.0.0.1 instead of localhost for maximum reliability on Windows
    url = f"http://127.0.0.1:5000/host?token={token}"
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Error opening browser automatically: {e}")

if __name__ == '__main__':
    config = load_config()
    local_ip = get_local_ip()
    port = 5000
    
    print("\n" + "="*60)
    print("                 LOCAL FILE DISTRIBUTOR")
    print("="*60)
    print(f" * Server is starting up...")
    print(f" * Access URL for Clients:  http://{local_ip}:{port}")
    print(f" * Access URL for Host:     http://localhost:{port}/host")
    print(f" * Host Remote Admin Token: {config.get('host_token')}")
    print(f" * To manage remotely, visit: http://{local_ip}:{port}/host?token={config.get('host_token')}")
    print("="*60 + "\n")
    
    # Start auto-open browser thread
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
