# -*- coding: utf-8 -*-

"""
Vercel Serverless Entry Point for Python Backend.

This script acts as the main entry point for all API requests when deployed on Vercel.
It initializes a Flask application and imports the routing logic from the original
local API server implementation. Vercel's build process discovers this file
(because it's in the /api directory) and converts it into a serverless function.

The original `py_local_api_server.py` is NOT used on Vercel; this file replaces it
for the production environment. However, all the core business logic from
`py_simple_evaluate.py` and `py_final_analysis.py` is reused.

"""

import sys
import os

# Add the src directory to the system path
# This is necessary for Vercel to find the modules in the `api/backend` directory.
# We are going one level up from `api/` to the project root, then into `api/`.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app object from the local server implementation
# Vercel will use this 'app' object as the handler for incoming requests.
from backend.py_local_api_server import app

# The 'app' object is now exposed for Vercel's runtime.
# When a request comes to /api/..., Vercel routes it to this Flask instance.
