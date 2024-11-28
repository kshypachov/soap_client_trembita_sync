# Посібник з розгортання REST клієнта в Docker

## Опис

Цей посібник допоможе розгорнути додаток у середовищі Docker

## Зміст

1. [Вимоги](#вимоги)
2. [Змінні оточення](#змінні-оточення)
3. [Як зібрати Docker-образ](#як-зібрати-docker-образ)
4. [Як запустити контейнер](#як-запустити-контейнер)
5. [Перегляд логів](#перегляд-логів)
6. [Використання змінних оточення для конфігурації](#використання-змінних-оточення-для-конфігурації)
7. [Використання конфігураційного файлу](#використання-конфігураційного-файлу)

## Вимоги

- Docker версії 20.10 і вище
- Docker Compose (якщо планується використання)
- Git (для клонування репозиторію)

## Змінні оточення

Додаток підтримує конфігурацію через змінні оточення. Ось основні параметри:

    •	USE_ENV_CONFIG – Вказує, чи потрібно використовувати змінні оточення для конфігурації замість файлу конфігурації. Якщо встановлено значення true, всі параметри будуть братися із змінних оточення, а не з файлу config.ini.
	•	TREMBITA_PROTOCOL – Протокол, який використовується для взаємодії з системою Трембіта. Можливі варіанти: http або https. Наприклад, http використовується для простого підключення, а https – для захищеного підключення з автентифікацією.
	•	TREMBITA_PURPOSE_ID – Ідентифікатор мети обробки персональних даних. Цей параметр використовується для інтеграції з Підсистемою моніторингу доступу до персональних даних (ПМДПД).
	•	TREMBITA_HOST – Хост або IP-адреса сервера Трембіта, до якого підключається клієнт. Це може бути FQDN або локальна IP-адреса, наприклад 10.0.20.235.
	•	CLIENT_INSTANCE – Ідентифікатор клієнтської підсистеми в системі Трембіта. Наприклад, test1 може бути тестовим інстансом для клієнта.
	•	CLIENT_MEMBERCLASS – Клас учасника системи Трембіта, наприклад GOV, який зазвичай використовується для урядових організацій.
	•	CLIENT_MEMBERCODE – Унікальний код клієнта в системі Трембіта. Наприклад, 10000004 – це код ЄДРПОУ організації-клієнта.
	•	CLIENT_SUBSYSTEMCODE – Код підсистеми організації-клієнта в системі Трембіта. Використовується для визначення конкретної підсистеми, яка буде обробляти запити. Наприклад, SUB_CLIENT.
	•	SERVICE_INSTANCE – Ідентифікатор інстансу сервісу в системі Трембіта, наприклад, test1. Це ідентифікатор сервісу, на який надсилаються запити.
	•	SERVICE_MEMBERCLASS – Клас учасника для сервісу, зазвичай такий самий, як і для клієнта (GOV).
	•	SERVICE_MEMBERCODE – Унікальний код організації-постачальника сервісу, наприклад 10000004, код ЄДРПОУ організації, яка надає сервіс.
	•	SERVICE_SERVICECODE – Код сервісу в системі Трембіта. Наприклад, py_sync – це код конкретного сервісу, який опублікований організацією-постачальником.
	•	SERVICE_SUBSYSTEMCODE – Код підсистеми організації-постачальника сервісу в системі Трембіта. Наприклад, SUB_SERVICE.
	•	LOGGING_LEVEL – Рівень деталізації повідомлень у логах. Можливі значення: DEBUG (найдетальніший), INFO, WARNING, ERROR, CRITICAL. Значення DEBUG виводить максимальну кількість інформації для налагодження програми.
 	•	LOGGING_FILENAME - Вказує шлюх де слід зберігати лог-файл
Приклад заповнення змінних оточення.
```env
- `USE_ENV_CONFIG`=true;
- `TREMBITA_PROTOCOL`=http;
- `TREMBITA_PURPOSE_ID`=1234567;
- `TREMBITA_HOST`=10.0.20.235;
- `CLIENT_INSTANCE`=test1;
- `CLIENT_MEMBERCLASS`=GOV;
- `CLIENT_MEMBERCODE`=10000004;
- `CLIENT_SUBSYSTEMCODE`=SUB_CLIENT;
- `SERVICE_INSTANCE`=test1;
- `SERVICE_MEMBERCLASS`=GOV;
- `SERVICE_MEMBERCODE`=10000004;
- `SERVICE_SERVICECODE`=py_sync;
- `SERVICE_SUBSYSTEMCODE`=SUB_SERVICE; 
- `LOGGING_LEVEL`=DEBUG
```

## Як зібрати Docker-образ

Щоб зібрати Docker-образ, виконайте наступну команду в кореневій директорії проєкту:

```bash
docker build -t web-client_trembita_sync_soap .
```

Ця команда створить Docker-образ з іменем web-client_trembita_sync_soap`, використовуючи Dockerfile, який знаходиться в поточній директорії.

## Як запустити контейнер

Щоб запустити контейнер з додатком, виконайте команду:

```bash
docker run -it --rm -p 5000:5000 \
    -e USE_ENV_CONFIG=true \
    -e TREMBITA_PROTOCOL=http \
    -e TREMBITA_PURPOSE_ID=1234567 \
    -e TREMBITA_HOST=10.0.20.235 \
    -e CLIENT_INSTANCE=test1 \
    -e CLIENT_MEMBERCLASS=GOV \
    -e CLIENT_MEMBERCODE=10000004 \
    -e CLIENT_SUBSYSTEMCODE=SUB_CLIENT \
    -e SERVICE_INSTANCE=test1 \
    -e SERVICE_MEMBERCLASS=GOV \ 
    -e SERVICE_MEMBERCODE=10000004 \
    -e SERVICE_SERVICECODE=py_sync \
    -e SERVICE_SUBSYSTEMCODE=SUB_SERVICE \
    -e LOGGING_LEVEL=DEBUG \
    web-client_trembita_sync_soap
```

- Прапор `-p 5000:5000` перенаправляє порт 8000 на локальній машині на порт 8000 всередині контейнера.

### Запуск з конфігураційним файлом

Ви можете запускати додаток, використовуючи конфігураційний файл замість змінних оточення. Для цього додайте файл `config.ini` в директорію додатка та вкажіть шлях до нього:

```bash
docker run -it --rm -p 5000:5000 \
    -v $(pwd)/config.ini:/app/config.ini \
    web-client_trembita_sync_soap
```

- Прапор `-v $(pwd)/config.ini:/app/config.ini` монтує локальний файл конфігурації в контейнер за шляхом `/app/config.ini`.

### Приклад конфігураційного файлу `config.ini`:

```ini
[trembita]
protocol = https
host = 192.168.99.150
purpose_id = ""
cert_path = certs
asic_path = asic
cert_file = cert.pem
key_file = key.pem
trembita_cert_file = trembita.pem

[client]
instance = test1
memberClass = GOV
memberCode = 10000003
subsystemCode = CLIENT

[service]
instance = test1
memberClass = GOV
memberCode = 10000003
subsystemCode = SERVICE
serviceCode = python_ssl

[logging]
filename = /tmp/file.log
filemode = a
format = %(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s
dateformat = %H:%M:%S
level = DEBUG # info warning debug
```

## Перегляд логів

Якщо ви налаштовуєте виведення логів у консоль, ви можете переглядати їх за допомогою команди:

```bash
docker logs <container_id>
```

Якщо логи зберігаються у файл (через змінну `LOG_FILENAME` або конфігураційний файл), ви можете налаштувати монтування директорії з логами на локальній машині:

```bash
docker run -it --rm -p 5000:5000 \
    -e LOGGING_FILENAME="/var/log/app.log" \
    -v $(pwd)/logs:/var/log \
    web-client_trembita_sync_soap
```

Тут `-v $(pwd)/logs:/var/log` монтує локальну директорію для збереження логів.

## Використання змінних оточення для конфігурації

Якщо ви хочете повністю покладатися на змінні оточення для конфігурації, переконайтеся, що `USE_ENV_CONFIG=true`. Наприклад:

```bash
docker run -it --rm -p 5000:5000 \
    -e USE_ENV_CONFIG=true \
    -e TREMBITA_PROTOCOL=http \
    -e TREMBITA_PURPOSE_ID=1234567 \
    -e TREMBITA_HOST=10.0.20.235 \
    -e CLIENT_INSTANCE=test1 \
    -e CLIENT_MEMBERCLASS=GOV \
    -e CLIENT_MEMBERCODE=10000004 \
    -e CLIENT_SUBSYSTEMCODE=SUB_CLIENT \
    -e SERVICE_INSTANCE=test1 \
    -e SERVICE_MEMBERCLASS=GOV \ 
    -e SERVICE_MEMBERCODE=10000004 \
    -e SERVICE_SERVICECODE=py_sync \
    -e SERVICE_SUBSYSTEMCODE=SUB_SERVICE \
    -e LOGGING_LEVEL=DEBUG \
    web-client_trembita_sync_soap
```

# Використання конфігураційного файлу

Якщо змінна `USE_ENV_CONFIG` не задана або встановлена в `false`, додаток буде використовувати конфігураційний файл для налаштування. Переконайтеся, що файл доступний у контейнері, як показано в розділі "Запуск з конфігураційним файлом".
