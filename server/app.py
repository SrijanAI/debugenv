# Entry point for openenv-core multi-mode deployment
# Imports the main FastAPI app from api/server.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.server import app

__all__ = ["app"]
