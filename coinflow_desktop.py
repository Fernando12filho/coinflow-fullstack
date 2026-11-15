"""Entry point for the CoinFlow desktop app (used by PyInstaller). See app/launcher.py."""
import sys

from app.launcher import main

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
