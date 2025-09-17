#!/bin/bash

# Start virtual display for headless GUI operations
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &

# Start Jupyter Lab
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token="" --NotebookApp.password=""