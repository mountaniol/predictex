# 🔧 Fix for "No module named 'toml'" Error

## Problem
When running the backend without virtual environment activation, Python cannot find the `toml` module which is needed to read `config.toml`.

## Solutions

### Solution 1: Use Virtual Environment (Recommended)

Always run the backend through the virtual environment:

```bash
# Navigate to main project directory
cd /media/AI/predictex/qna-evaluator

# Activate virtual environment
source venv/bin/activate

# Now start the backend
cd question-creator
./start-backend.sh

# OR use the new wrapper script
./run-backend-with-venv.sh
```

### Solution 2: Install toml System-Wide

If you have sudo access:

```bash
sudo apt-get update
sudo apt-get install python3-toml
```

### Solution 3: Use the Wrapper Script

We've created `run-backend-with-venv.sh` that automatically:
- Activates the virtual environment
- Ensures toml is installed
- Starts the backend

```bash
cd /media/AI/predictex/qna-evaluator/question-creator
./run-backend-with-venv.sh
```

### Solution 4: Create a systemd Service

For production, create a systemd service that always uses the virtual environment:

```ini
# /etc/systemd/system/question-creator-backend.service
[Unit]
Description=Question Creator Backend
After=network.target

[Service]
Type=simple
User=se
WorkingDirectory=/media/AI/predictex/qna-evaluator/question-creator/backend
Environment="PATH=/media/AI/predictex/qna-evaluator/venv/bin"
ExecStart=/media/AI/predictex/qna-evaluator/venv/bin/python server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable question-creator-backend
sudo systemctl start question-creator-backend
```

## Why This Happens

1. The `toml` module is installed in the virtual environment (`venv/lib/python3.12/site-packages/`)
2. When you run Python without activating the venv, it uses system Python which doesn't have `toml`
3. Modern Ubuntu/Debian systems prevent installing packages globally with pip (PEP 668)

## Quick Test

To verify the fix works:

```bash
# With virtual environment
cd /media/AI/predictex/qna-evaluator
source venv/bin/activate
python -c "import toml; print('✅ toml module found')"

# Test the backend
cd question-creator
./run-backend-with-venv.sh
```

Then test the API:
```bash
curl http://192.168.1.50:3004/api/health
```

## Current Status

- ✅ `toml` is installed in virtual environment
- ✅ `run-backend-with-venv.sh` created for easy startup
- ✅ `start-backend.sh` updated to check for venv
- ⚠️ Always use virtual environment when running the backend