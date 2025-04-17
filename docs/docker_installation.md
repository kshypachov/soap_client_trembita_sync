# Розгортання вебклієнта в Docker

## Вимоги

| ПЗ             |   Версія   | Примітка                     |
|:---------------|:----------:|------------------------------|
| Docker         | **20.10+** |                              |
| Docker Compose |   10.5+    | Якщо планується використання |
| Git            |            | Для клонування репозиторію   |

## Змінні оточення

Вебклієнт підтримує конфігурацію через змінні оточення. 
Нижче наведено основні параметри:
- `USE_ENV_CONFIG` – Керує використанням змінних оточення для конфігурації. Якщо встановлено значення `true`, всі параметри будуть братися із змінних оточення, а не з файлу `config.ini`.
- `TREMBITA_PROTOCOL` – Протокол, який використовується для взаємодії з системою Трембіта. Можливі варіанти: http або https. Наприклад, http використовується для простого підключення, а https – для захищеного підключення з автентифікацією.
- `TREMBITA_PURPOSE_ID` – Ідентифікатор мети обробки персональних даних. Цей параметр використовується для інтеграції з Підсистемою моніторингу доступу до персональних даних (ПМДПД).
- `TREMBITA_HOST` – Хост або IP-адреса сервера Трембіта, до якого підключається клієнт. Це може бути FQDN або локальна IP-адреса, наприклад 10.0.20.235.
- `CLIENT_INSTANCE` – Ідентифікатор клієнтської підсистеми в системі Трембіта. Наприклад, SEVDEIR-TEST може бути тестовим інстансом для клієнта.
- `CLIENT_MEMBERCLASS` – Клас учасника системи Трембіта, наприклад GOV, який зазвичай використовується для урядових організацій.
- `CLIENT_MEMBERCODE` – Унікальний код клієнта в системі Трембіта. Наприклад, 10000004 – це код ЄДРПОУ організації-клієнта.
- `CLIENT_SUBSYSTEMCODE` – Код підсистеми організації-клієнта в системі Трембіта. Використовується для визначення конкретної підсистеми, яка буде обробляти запити. Наприклад, SUB_CLIENT.
- `SERVICE_INSTANCE` – Ідентифікатор інстансу сервісу в системі Трембіта, наприклад, SEVDEIR-TEST. Це ідентифікатор сервісу, на який надсилаються запити.
- `SERVICE_MEMBERCLASS` – Клас учасника для сервісу, зазвичай такий самий, як і для клієнта (GOV).
- `SERVICE_MEMBERCODE` – Унікальний код організації-постачальника сервісу, наприклад 10000004, код ЄДРПОУ організації, яка надає сервіс.
- `SERVICE_SERVICECODE` – Код сервісу в системі Трембіта. Наприклад, py_sync – це код конкретного сервісу, який опублікований організацією-постачальником.
- `SERVICE_SUBSYSTEMCODE` – Код підсистеми організації-постачальника сервісу в системі Трембіта. Наприклад, SUB_SERVICE.
- `SERVICE_SERVICEVERSION` - Версія сервісу організації-постачальника сервісу в системі Трембіта.
- `LOGGING_LEVEL` – Рівень деталізації повідомлень у логах. Можливі значення: DEBUG (найдетальніший), INFO, WARNING, ERROR, CRITICAL. Значення DEBUG виводить максимальну кількість інформації для налагодження програми.
- `LOGGING_FILENAME` - Ім'я файлу для логування. Якщо значення параметра порожнє, логи будуть виводитися в консоль (stdout).

## Збір Docker-образу

Для того, щоб зібрати Docker-образ, необхідно:

1. Клонувати репозиторій:

```bash
git clone https://github.com/kshypachov/soap_client_trembita_sync.git
```

2. Перейти до директорії з вебклієнтом:

```bash
cd soap_client_trembita_sync
```

3. Виконати наступну команду в кореневій директорії проєкту:
```bash
sudo docker build -t web-client_trembita_sync_soap .
```

Дана команда створить Docker-образ з іменем `my-soap-app`, використовуючи Dockerfile, який знаходиться в поточній директорії.

## Запуск та використання контейнера зі змінними оточення

Щоб запустити контейнер з додатком, виконайте команду:

```bash
sudo docker run -it --rm -p 5000:5000 \
    -e USE_ENV_CONFIG=true \
    -e TREMBITA_PROTOCOL=http \
    -e TREMBITA_PURPOSE_ID=1234567 \
    -e TREMBITA_HOST=10.0.20.235 \
    -e CLIENT_INSTANCE=SEVDEIR-TEST \
    -e CLIENT_MEMBERCLASS=GOV \
    -e CLIENT_MEMBERCODE=10000004 \
    -e CLIENT_SUBSYSTEMCODE=SUB_CLIENT \
    -e SERVICE_INSTANCE=SEVDEIR-TEST \
    -e SERVICE_MEMBERCLASS=GOV \ 
    -e SERVICE_MEMBERCODE=10000004 \
    -e SERVICE_SERVICECODE=py_sync \
    -e SERVICE_SUBSYSTEMCODE=SUB_SERVICE \
    -e LOGGING_LEVEL=DEBUG \
    web-client_trembita_sync_soap

```

де:
- параметр `-p 5000:5000` перенаправляє порт 5000 на локальній машині на порт 5000 всередині контейнера.
- інші змінні перелічені в пункті [Змінні оточення](#змінні-оточення)

Якщо планується повністю використовувати змінні оточення для конфігурації, необхідно переконатись, що `USE_ENV_CONFIG=true`.

Наприклад:

```bash
sudo docker run -it --rm -p 5000:5000 \
    -e USE_ENV_CONFIG=true \
    -e TREMBITA_PROTOCOL=http \
    -e TREMBITA_PURPOSE_ID=1234567 \
    -e TREMBITA_HOST=10.0.20.235 \
    -e CLIENT_INSTANCE=SEVDEIR-TEST \
    -e CLIENT_MEMBERCLASS=GOV \
    -e CLIENT_MEMBERCODE=10000004 \
    -e CLIENT_SUBSYSTEMCODE=SUB_CLIENT \
    -e SERVICE_INSTANCE=SEVDEIR-TEST \
    -e SERVICE_MEMBERCLASS=GOV \ 
    -e SERVICE_MEMBERCODE=10000004 \
    -e SERVICE_SERVICECODE=py_sync \
    -e SERVICE_SUBSYSTEMCODE=SUB_SERVICE \
    -e LOGGING_LEVEL=DEBUG \
    web-client_trembita_sync

```

### Запуск та використання контейнера з конфігураційним файлом

Контейнер з вебклієнтом можна запустити використовуючи конфігураційний файл замість змінних оточення. 
Для цього необхідно створити файл `config.ini` в директорії вебклієнта та вказати шлях до нього:

```bash
sudo docker run -it --rm -p 5000:5000 \
    -v $(pwd)/config.ini:/app/config.ini \
    web-client_trembita_sync_soap
```
де параметр `-v $(pwd)/config.ini:/app/config.ini` монтує локальний файл конфігурації в контейнер за шляхом `/app/config.ini`.

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

## Перегляд журналів подій

Якщо виведення журналів подій налаштоване у консоль, переглядати їх можна за допомогою команди:

```bash
docker logs <container_id>
```

В разі, якщо журнали подій зберігаються у файл (через змінну оточення `LOG_FILENAME` або конфігураційний файл), можна налаштувати монтування директорії з журналами подій на локальній машині наступним чином:

```bash
docker run -it --rm -p 5000:5000 \
    -e LOGGING_FILENAME="/var/log/app.log" \
    -v $(pwd)/logs:/var/log \
    web-client_trembita_sync
```

де параметр `-v $(pwd)/logs:/var/log` монтує локальну директорію для збереження журналів подій.

##
Матеріали створено за підтримки проєкту міжнародної технічної допомоги «Підтримка ЄС цифрової трансформації України (DT4UA)».
