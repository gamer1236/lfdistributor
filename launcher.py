import os
import sys
import subprocess

def main():
    # Get the directory where this launcher executable is located
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # 1. Try launching the compiled portable executable if it exists
    release_exe = os.path.join(base_dir, "LFDistributor_Release", "LFDistributor.exe")
    if os.path.exists(release_exe):
        try:
            # Launch the executable in a new process/console and exit the launcher
            subprocess.Popen([release_exe], creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            sys.exit(0)
        except Exception as e:
            print(f"Error starting portable executable: {e}")
            input("Press Enter to exit...")
            sys.exit(1)
            
    # 2. Try launching the development Flask server if virtual env is present
    dev_python = os.path.join(base_dir, "venv", "Scripts", "python.exe")
    dev_app = os.path.join(base_dir, "app.py")
    if os.path.exists(dev_python) and os.path.exists(dev_app):
        print("Starting Local File Distributor in development mode...")
        try:
            subprocess.run([dev_python, dev_app])
            sys.exit(0)
        except Exception as e:
            print(f"Error starting development server: {e}")
            input("Press Enter to exit...")
            sys.exit(1)
            
    # 3. Error case if neither is found
    print("Error: Local File Distributor executable or development environment not found!")
    print("Please run build.py to compile the project first.")
    input("Press Enter to exit...")
    sys.exit(1)

if __name__ == "__main__":
    main()
