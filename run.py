#!/usr/bin/env python3
"""
Run the Mail Agent application
"""
import os
import sys


# Import and run the application
from mail_agent.app import init_app

if __name__ == '__main__':
    app = init_app()
    app.run(debug=True, port=5000)
