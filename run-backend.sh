#!/bin/bash

# Путь к директории с виртуальным окружением
VENV_DIR="venv"

# 1. Проверяем, существует ли директория venv
if [ ! -d "$VENV_DIR" ]; then
  echo ">>> Creating virtual environment in '$VENV_DIR'..."
  python3 -m venv $VENV_DIR
  if [ $? -ne 0 ]; then
    echo "!!! Failed to create virtual environment."
    exit 1
  fi
fi

# 2. Активируем виртуальное окружение
echo ">>> Activating virtual environment..."
source $VENV_DIR/bin/activate

# 3. Устанавливаем зависимости из корневого requirements.txt
echo ">>> Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
  echo "!!! Failed to install requirements."
  exit 1
fi

# 4. Запускаем Python backend как модуль, чтобы работали относительные импорты
echo ">>> Starting Python backend server..."
python -u -m src.backend.py_local_api_server
