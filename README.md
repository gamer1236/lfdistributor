# lfdistributor
Local File Distributor (lfdistributor)
======================================

Local File Distributor (LFD) is a lightweight, portable Python web application that acts as a local file-sharing server. It allows hosts to distribute files to clients over a Local Area Network (LAN) via a sleek, responsive web interface. 

The application is completely self-contained and portable on Windows, meaning it runs on any Windows PC without requiring a Python installation, pip, dependencies, or internet connectivity.

---

KEY FEATURES
============

1. Standalone Portability (No Python Needed)
   - Packaged with PyInstaller into a self-contained portable distribution folder.
   - Can run directly from a portable USB drive or external SSD without installation.

2. One-Click Launch
   - Double-clicking the compiled 'LFDistributor.exe' immediately boots the Flask server and opens the Host Portal dashboard in the default web browser.

3. Auto Connection Sharing & QR Code
   - Automatically detects the host's active local LAN IP address on startup.
   - Generates a dynamic QR code containing the Client Portal URL so mobile devices and other computers on the network can connect instantly.

4. Host Administration Portal
   - Dynamic Directory Browser: Allows the host to browse their Windows filesystem and change the active shared directory through the browser.
   - Password Protection: Optional password restriction to protect files from unauthorized clients.
   - Remote Management: Secured using a unique Host Administration Token for secure remote administration.
   - File Uploads: Supports chunk-by-chunk streaming uploads directly to the active shared folder.
   - Real-time Stats: Shows shared files count, total size, and individual file download counters.

5. Client Portal
   - Clean, modern, responsive web dashboard where clients can view, search, sort, and download shared files.
   - Supports HTTP Range headers (crucial for streaming video/audio and resuming downloads).

6. Error Handling & Logging
   - Creates necessary directories (config, logs, shared, assets) automatically.
   - Intercepts and writes all print statements and traceback errors to 'logs/server.log'.
   - Native Windows popups warn the user of missing files or corrupt releases instead of crashing silently.

---

FOLDER STRUCTURE
================

```
LFDistributor_Release/
├── LFDistributor.exe         # Standalone compiled application executable
├── Launch_LFDistributor.bat  # Backup launcher for double-clicking
├── _internal/                # Bundled Python runtime, Flask, and dependencies
├── shared/                   # Default shared folder for client downloads
├── config/                   # Location of 'config.json' settings
├── logs/                     # Location of 'server.log' application logs
└── assets/                   # Optional folder for resources/assets
```

---

INSTRUCTIONS FOR USE
====================

A. Running the Portable Release (End Users)
-------------------------------------------
1. Copy or extract the 'LFDistributor_Release/' folder onto any Windows 10/11 PC.
2. Double-click the main executable:
   `LFDistributor.exe`
3. A command prompt window will open showing the server console, and your default web browser will automatically open the Host Portal (http://localhost:5000/host).
4. Drop the files you want to share into the 'shared/' folder inside the application directory. You can also change the shared folder to any directory on your computer by clicking "Browse Directories" on the Host dashboard.
5. Have clients scan the displayed QR code or navigate to the connection URL (e.g. http://192.168.x.x:5000) on their devices.
6. To stop the server, simply close the command prompt window.

B. Running in Development Mode (Developers)
-------------------------------------------
1. Navigate to the project root directory.
2. If you are starting for the first time, activate the virtual environment and install dependencies:
   `.\venv\Scripts\activate`
   `pip install -r requirements.txt`
3. Double-click the root wrapper launcher:
   `LFDistributor.exe`
   (This launcher detects the source files and starts the Flask server in development mode).
4. Make code modifications in 'app.py' and test changes using the automated test suite:
   `.\venv\Scripts\python.exe -m unittest test_app.py`

C. Compiling a New Release
--------------------------
To compile code changes into a new portable distribution package:
1. Run the build automation script:
   `.\venv\Scripts\python.exe build.py`
2. This script compiles the project, bundles templates/static assets, and updates the compiled release folder 'LFDistributor_Release/' and the root launcher.
