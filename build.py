import os
import shutil
import subprocess
import sys

def build():
    print("=" * 60)
    print("         LOCAL FILE DISTRIBUTOR BUILD AUTOMATION")
    print("=" * 60)

    # 1. Install/Verify PyInstaller in the current environment
    print("[1/5] Ensuring PyInstaller is installed...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("[SUCCESS] PyInstaller is ready!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install PyInstaller: {e}")
        sys.exit(1)

    # 2. Clean previous build artifacts
    print("\n[2/5] Cleaning up old build artifacts...")
    dirs_to_clean = ["build", "dist", "LFDistributor_Release"]
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"  Removing directory: {d}")
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"  [WARNING] Could not remove {d}: {e}")

    # 3. Compile the Flask app using PyInstaller
    print("\n[3/5] Running PyInstaller to bundle the application...")
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--name=LFDistributor",
        "--add-data=templates;templates",
        "--add-data=static;static",
        "--clean",
        "app.py"
    ]
    
    print(f"  Running command: {' '.join(pyinstaller_cmd)}")
    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("[SUCCESS] Package compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] PyInstaller compilation failed: {e}")
        sys.exit(1)

    print("\nCompiling the workspace launcher executable...")
    pyinstaller_launcher_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name=LFDistributor_Launcher",
        "--clean",
        "launcher.py"
    ]
    print(f"  Running command: {' '.join(pyinstaller_launcher_cmd)}")
    try:
        subprocess.run(pyinstaller_launcher_cmd, check=True)
        print("[SUCCESS] Workspace launcher compilation completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Launcher compilation failed: {e}")
        sys.exit(1)

    # 4. Create portable folder structure
    print("\n[4/5] Constructing the portable release directory...")
    release_dir = "LFDistributor_Release"
    internal_dist = os.path.join("dist", "LFDistributor")

    if not os.path.exists(internal_dist):
        print(f"[ERROR] Compiled dist folder '{internal_dist}' was not found!")
        sys.exit(1)

    # Ensure empty target directories exist
    required_folders = ["shared", "config", "logs", "assets"]
    for folder in required_folders:
        folder_path = os.path.join(release_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"  Created portable folder: {folder_path}")

    # Copy executable and internal packages
    print("  Copying executable files...")
    shutil.copy(os.path.join(internal_dist, "LFDistributor.exe"), os.path.join(release_dir, "LFDistributor.exe"))
    shutil.copytree(os.path.join(internal_dist, "_internal"), os.path.join(release_dir, "_internal"), dirs_exist_ok=True)

    # Copy launcher executable to workspace root
    launcher_src = os.path.join("dist", "LFDistributor_Launcher.exe")
    launcher_dst = "LFDistributor.exe"
    if os.path.exists(launcher_src):
        try:
            shutil.copy(launcher_src, launcher_dst)
            print(f"  Copied workspace root launcher to: {launcher_dst}")
        except Exception as e:
            print(f"  [WARNING] Could not copy launcher to workspace root: {e}")

    # Copy welcome text file to shared if it exists in the dev files
    welcome_src = os.path.join("shared", "welcome_to_local_file_distributor.txt")
    welcome_dst = os.path.join(release_dir, "shared", "welcome_to_local_file_distributor.txt")
    if os.path.exists(welcome_src):
        shutil.copy(welcome_src, welcome_dst)
        print("  Copied welcome_to_local_file_distributor.txt to release shared folder.")
    else:
        # Create a basic file if not exists
        with open(welcome_dst, "w", encoding="utf-8") as f:
            f.write("Welcome to Local File Distributor!\nPlace files you want to share in this folder.")
        print("  Created default welcome message in release shared folder.")

    # 5. Generate launcher batch script
    print("\n[5/5] Creating launcher batch script...")
    launcher_path = os.path.join(release_dir, "Launch_LFDistributor.bat")
    launcher_content = """@echo off
title Local File Distributor Launcher
cd /d "%~dp0"
echo Starting Local File Distributor...
start "" "%~dp0LFDistributor.exe"
"""
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher_content)
    print(f"  Created: {launcher_path}")

    print("\n" + "=" * 60)
    print(" BUILD SUCCESSFUL! Portable release is ready in: LFDistributor_Release/")
    print("=" * 60)
    print("Release directory structure:")
    print("  LFDistributor_Release/")
    print("    |-- LFDistributor.exe         (Standalone executable)")
    print("    |-- Launch_LFDistributor.bat  (Double-click to start)")
    print("    |-- _internal/                (Internal Python dependencies)")
    print("    |-- shared/                   (Shared files folder)")
    print("    |-- config/                   (Configuration files)")
    print("    |-- logs/                     (Application logs)")
    print("    +-- assets/                   (Optional assets)")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    build()
