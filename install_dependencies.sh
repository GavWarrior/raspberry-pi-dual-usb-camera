#!/bin/bash
#
# Script to install all dependencies required for the dual USB camera web app.
# This script should be run on a Raspberry Pi (or other Debian‑based Linux
# distribution) with sudo privileges. It installs OpenCV, Flask and numpy via
# the apt package manager and pip. The apt packages ensure that native
# dependencies (such as libopencv) are present, while pip ensures that the
# Python modules are available for your virtual environment.

set -euo pipefail

echo "Updating package lists..."
sudo apt-get update -y

echo "Installing system libraries for OpenCV and Flask..."
sudo apt-get install -y python3-opencv python3-flask python3-numpy

# Optionally install OpenCV via pip for more recent versions. You may comment
# this line out if the apt packaged version meets your needs. On Raspberry Pi
# systems this can take a while to compile, so precompiled wheels are preferred.
echo "Installing Python packages via pip..."
python3 -m pip install --upgrade pip
python3 -m pip install flask opencv-python-headless numpy

echo "Dependencies installed successfully."
