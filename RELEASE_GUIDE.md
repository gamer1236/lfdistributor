# Local File Distributor - Release Management Guide

This document explains the folder structure and how to package and release new versions of the Local File Distributor application.

---

## 1. Application Folder Structure

The compiled release is located in the `LFDistributor_Release/` folder. It is designed to be completely portable and self-contained, meaning it does not require Python, pip, or an internet connection to run.

```
LFDistributor_Release/
├── LFDistributor.exe         # Main application compiled executable
├── Launch_LFDistributor.bat  # Quick launcher for end users (double-click)
├── _internal/                # Bundled Python runtime, Flask, and dependencies
├── shared/                   # Files shared with clients (empty/welcome file)
├── config/                   # Configuration settings folder (config.json)
├── logs/                     # Application and web server log files (server.log)
└── assets/                   # Optional directory for resources/assets
```

---

## 2. Generating a New Release

To package a new version of the application (e.g., after modifying `app.py`, adding templates, or updating dependencies):

1. **Verify Development Mode**:
   Ensure all automated tests pass successfully:
   ```powershell
   .\venv\Scripts\python.exe -m unittest test_app.py
   ```

2. **Run the Build Script**:
   Execute the automated build script `build.py` using the project's Python virtual environment:
   ```powershell
   .\venv\Scripts\python.exe build.py
   ```

3. **How the Build Script Works**:
   * Installs/updates `pyinstaller` inside the virtual environment automatically.
   * Cleans up any previous `dist/`, `build/`, and `LFDistributor_Release/` directories.
   * Compiles the Flask application using PyInstaller with `--onedir` mode.
   * Bundles the HTML templates and static styles/scripts internally into the executable bundle (`_internal/`).
   * Copies the compiled executable and internal packages to `LFDistributor_Release/`.
   * Pre-creates the portable directories (`shared`, `config`, `logs`, `assets`) and includes the default `Launch_LFDistributor.bat` launcher.

4. **Distribution**:
   Zip the entire `LFDistributor_Release` directory and distribute it to users.
   * Users only need to extract the zip file and double-click `Launch_LFDistributor.bat` or `LFDistributor.exe`.

---

## 3. Configuration & Troubleshooting

### Config File Location
The configuration file is automatically created on the first launch as `config/config.json`. It stores user settings such as:
* Path to the active shared directory (defaulting to the portable `shared/` folder).
* Password protection toggle and credentials.
* The Host Administration Token used for authentication.

### Checking Logs
If the application crashes, does not start, or displays errors, check the logs folder:
* `logs/server.log` contains stdout print logs, Flask web server request info, and detailed traceback logs for any unhandled exceptions.

### Missing Resources Error
If the executable is launched and a user-friendly popup window appears warning about missing files, the compiled release package is likely incomplete or corrupted. Regenerate the release using `build.py` to restore all templates and static assets inside the `_internal` bundle.
