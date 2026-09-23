import sys
import os

# Add project root to sys.path so server, db, renderer can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app
