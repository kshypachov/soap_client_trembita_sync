#!/bin/bash

# Оновлення пакетів і встановлення необхідних залежностей
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv

# Клонування репозиторію
git clone https://github.com/kshypachov/soap_client_trembita_sync.git
cd soap_client_trembita_sync

# Створення та активація віртуального оточення
python3 -m venv venv
source venv/bin/activate

# Встановлення залежностей
pip install -r requirements.txt

# Створення Unit файлу системної служби для systemd
SERVICE_FILE=/etc/systemd/system/soap_sync_client.service

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Flask Application
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Перезавантаження systemd для застосування змін
sudo systemctl daemon-reload

# Увімкнення Flask-застосунку
sudo systemctl enable soap_sync_client
