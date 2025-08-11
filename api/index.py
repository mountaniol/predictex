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
from os.path import dirname, abspath

# Add the parent directory of 'api' to the Python path
# This allows us to use absolute imports from the project root
sys.path.append(dirname(dirname(abspath(__file__))))

# Now, we can import the Flask app object from the backend module
# This path is relative to the project root after the sys.path modification
from api.backend.py_local_api_server import app

# The 'app' variable is now exposed for Vercel's WSGI server to use.
# For local development, you would still run py_local_api_server.py directly.
