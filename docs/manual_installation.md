# Інсталяція клієнта вручну

## Опис 
Також існує можливість встановлення вебклієнту вручну, без застосування скрипта.

Для початку роботи потрібно мати чисту систему Ubuntu, всі необхідні пакети та репозиторії будуть підключені в ході виконання встановлення.

**Для того, щоб встановити даний вебклієнт вручну необхідно:**

### 1. Встановити необхідні пакети:

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv
```

- **Важливо:** Якщо версія Python нижче 3.10, клієнт працювати не буде.

### 2. Клонувати репозиторій

```bash
git clone https://github.com/kshypachov/soap_client_trembita_sync.git
```

### 3. Перейти до директорії з вебклієнтом

```bash
cd soap_client_trembita_sync
```

### 4. Створити віртуальне середовище
```bash
python3 -m venv venv
```

### 5. Активувати віртуальне середовище
```bash
source venv/bin/activate
```

### 6. Встановити залежності
```bash
pip install -r requirements.txt
```

### 7. Виконати конфігурацію вебклієнту згідно [настанов з конфігурації](./configuration.md)

### 8. Створити systemd unit-файл для запуску вебсервісу:

```bash
sudo bash -c "cat > /etc/systemd/system/soap_sync_client.service" << EOL
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
```

9. Перезавантажити конфігурацію systemd:

```bash
sudo systemctl daemon-reload
```

10. Додати сервіс до автозапуску

```bash
sudo systemctl enable soap_sync_client
```

##
Матеріали створено за підтримки проєкту міжнародної технічної допомоги «Підтримка ЄС цифрової трансформації України (DT4UA)».
