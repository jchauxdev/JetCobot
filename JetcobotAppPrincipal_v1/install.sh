#!/bin/bash
set -e

sudo apt install -y python3-tk
pip3 install -r "$(dirname "$0")/requirements.txt"
