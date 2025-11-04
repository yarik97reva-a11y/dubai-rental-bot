#!/usr/bin/env python3
"""
Simple bot launcher that works from project root
"""
import os
import sys

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Change to src directory for bot to work correctly
os.chdir(src_dir)

# Import and run bot
from bot import main

if __name__ == '__main__':
    main()
