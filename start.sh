#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Flask server..."
cd "$SCRIPT_DIR"
source venv/bin/activate
exec gunicorn -w 1 -b 127.0.0.1:8000 app:app
