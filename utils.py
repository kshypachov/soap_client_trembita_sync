import configparser
import uuid
import re
from urllib.parse import quote
import requests
from urllib.parse import urlencode

from zeep import Client, Settings
from zeep.transports import Transport
from zeep.plugins import HistoryPlugin
from zeep.helpers import serialize_object
from requests import Session

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import os
import logging

logger = logging.getLogger(__name__)

#"http://{trembita_ip}/wsdl?xRoadInstance={trebmita_instance}&memberClass={trembita_member_clacc}&memberCode={trembita_member_code}&subsystemCode={trembita_subsystem_code}&serviceCode={trembita_service_code}"&serviceVersion={trembita_service_version}
#Перелік імен сервісів з якими буде вестись обмін. Імена жорстко задані на стороні сервіса, тому не винесено у конфігурацію
serv_create_person = "create_person"
serv_get_person_by_parameter = "get_person_by_parameter"
serv_edit_person = "edit_person"
serv_delete_person_by_unzr = "delete_person_by_unzr"

class Config:
    def __init__(self, filename):
        # Перевіряємо, чи встановлена змінна оточення USE_ENV_CONFIG в true
        use_env_config = os.getenv("USE_ENV_CONFIG", "false").lower() == "true"

        if not use_env_config:
            # Якщо змінна USE_ENV_CONFIG не встановлена в true, читаємо конфігураційний файл
            self.parser = configparser.ConfigParser(interpolation=None)
            self.parser.read(filename)
        else:
            # Якщо змінна USE_ENV_CONFIG встановлена в true, ігноруємо конфігураційний файл
            self.parser = None

        # Функція для отримання значення з змінної оточення або конфігураційного файлу
        def get_config_value(section, option, default=None, required=False):
            env_var = f"{section.upper()}_{option.upper()}"
            if use_env_config:
                # Якщо використовуємо змінні оточення, зчитуємо значення тільки з них
                value = os.getenv(env_var, default)
            else:
                # Якщо змінна USE_ENV_CONFIG пуста, використовуємо тільки файл конфігурації
                value = self.parser.get(section, option, fallback=default)

            # Перевірка на обов'язковість параметра
            if required and not value:
                if use_env_config:
                    err_str = f"Помилка: Змінна оточення '{section.upper()}_{option.upper()}' є обовʼязковою. Задайте її значення будь ласка."
                else:
                    err_str = f"Помилка: У секції '[{section}]' відсутній обовʼязковий параметр '{option}' чи його значення не задано. Задайте його значення у конфігураційному файлі, будь ласка."
                logger.critical(err_str)
                raise ValueError(err_str)#

            return value

        # Зчитування конфігурації
        # Секція Трембіта
        self.trembita_protocol = get_config_value('trembita', 'protocol', required=True)
        self.trembita_host = get_config_value('trembita', 'host', required=True)
        self.trembita_purpose = get_config_value('trembita', 'purpose_id', '')
        self.cert_path = get_config_value('trembita', 'cert_path', 'certs')
        self.asic_path = get_config_value('trembita', 'asic_path', 'asic')
        self.cert_file = get_config_value('trembita', 'cert_file', 'cert.pem')
        self.key_file = get_config_value('trembita', 'key_file', 'key.pem')
        self.tembita_cert_file = get_config_value('trembita', 'trembita_cert_file' , 'trembita.pem')
        self.trembita_user_id  = get_config_value('trembita', 'user_id')
        # Секція ідентифікаторів клієнтської підсистеми
        self.client_instance = get_config_value('client', 'instance', required=True)
        self.client_org_type = get_config_value('client', 'memberClass', required=True)
        self.client_org_code = get_config_value('client', 'memberCode', required=True)
        self.client_org_sub = get_config_value('client', 'subsystemCode', required=True)
        # Секція ідентифікаторів сервісу
        self.service_instance = get_config_value('service', 'instance', required=True)
        self.service_org_type = get_config_value('service', 'memberClass', required=True)
        self.service_org_code = get_config_value('service', 'memberCode', required=True)
        self.service_org_sub = get_config_value('service', 'subsystemCode', required=True)

        # Параметри логування
        self.log_filename = get_config_value('logging', 'filename')
        self.log_filemode = get_config_value('logging', 'filemode', 'a')
        self.log_format = get_config_value('logging', 'format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.log_dateformat = get_config_value('logging', 'dateformat', '%Y-%m-%d %H:%M:%S')
        self.log_level = get_config_value('logging', 'level', 'INFO', required=True)

    def get(self, section, option):
        return self.parser.get(section, option)

def configure_logging(config_instance):
    log_filename = config_instance.log_filename
    log_filemode = config_instance.log_filemode
    log_format = config_instance.log_format
    log_datefmt = config_instance.log_dateformat
    log_level = config_instance.log_level

    #Якщо log_filename не передано, логування відбувається у консоль.
    if log_filename:
        # Логування у файл
        logging.basicConfig(
            filename=log_filename,
            filemode=log_filemode,
            format=log_format,
            datefmt=log_datefmt,
            level=getattr(logging, log_level, logging.INFO)
        )
        logger.info("Логування налаштовано")

    else:
        # Логування в консоль для Docker
        logging.basicConfig(
            format=log_format,
            datefmt=log_datefmt,
            level=log_level,
            handlers=[logging.StreamHandler()]  # Вывод в stdout
        )

def download_asic_from_trembita(queryId: str, config_instance):
    # https: // sec1.gov / signature? & queryId = abc12345 & xRoadInstance = SEVDEIR-TEST & memberClass = GOV & memberCode =
    # 12345678 & subsystemCode = SUB
    # Отримання ASIC контейнера з ШБО за допомогою GET-запиту
    asics_dir = config_instance.asic_path  # Отримуємо з конфігураційного файлу шлях до директорії, куди слід зберігати asic контейнери

    query_params = {
        "queryId": queryId,
        "xRoadInstance": config_instance.client_instance,
        "memberClass": config_instance.client_org_type,
        "memberCode": config_instance.client_org_code,
        "subsystemCode": config_instance.client_org_sub
    }

    if config_instance.trembita_protocol == "https":
        url = f"https://{config_instance.trembita_host}/signature"
        logger.info(f"Спроба завантажити ASIC з ШБО з URL: {url} та параметрами: {query_params}")

        try:
            # Надсилаємо GET-запит для завантаження файлу з архівом повідомлень
            response = requests.get(url, stream=True, params=query_params,
                                    cert=(os.path.join(config_instance.cert_path, config_instance.cert_file),
                                          os.path.join(config_instance.cert_path, config_instance.key_file)),
                                    verify=os.path.join(config_instance.cert_path, config_instance.tembita_cert_file))
            response.raise_for_status()

            logger.info(f"Успішно отримано відповідь від сервера з кодом: {response.status_code}")

            # Спроба отримати ім'я файлу з заголовку Content-Disposition
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                # Паттерн для визначення імені файлу
                filename_match = re.findall('filename="(.+)"', content_disposition)
                if filename_match:
                    local_filename = filename_match[0]
                else:
                    local_filename = 'downloaded_file.ext'
            else:
                # Якщо заголовку немає, використовуємо ім'я за замовчуванням
                local_filename = 'downloaded_file.ext'

            # Відкриваємо локальний файл в режимі запису байтів
            with open(f"{asics_dir}/{local_filename}", 'wb') as file:
                # Проходимо по частинах відповіді і записуємо їх у файл
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            logger.info(f'Файл успішно завантажено та збережено як:  {local_filename}')
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка під час завантаження файлу: {e}")
            raise
    else:

        logger.error("Функція download_asic_from_trembita працює тільки з протоколом https")
        raise ValueError("Ця функція процює тільки якщо протокол роботи з ШБО Трембіти - https")

# def download_asic_from_trembita(queryId: str, config_instance):
#     # https: // sec1.gov / signature? & queryId = abc12345 & xRoadInstance = SEVDEIR-TEST & memberClass = GOV & memberCode =
#     # 12345678 & subsystemCode = SUB
#     # Отримання ASIC контейнера з ШБО за допомогою GET-запиту
#     asics_dir = config_instance.asic_path  # Отримуємо з конфігураційного файлу шлях до директорії, куди слід зберігати asic контейнери
#
#     query_params = {
#         "queryId": queryId,
#         "xRoadInstance": config_instance.client_instance,
#         "memberClass": config_instance.client_org_type,
#         "memberCode": config_instance.client_org_code,
#         "subsystemCode": config_instance.client_org_sub
#     }
#     try:
#         if config_instance.trembita_protocol == "https":
#             url = f"https://{config_instance.trembita_host}/signature"
#             logger.info(f"Спроба завантажити ASIC з ШБО з URL: {url} та параметрами: {query_params}")
#             response = requests.get(url, stream=True, params=query_params,
#                                     cert=(os.path.join(config_instance.cert_path, config_instance.cert_file),
#                                           os.path.join(config_instance.cert_path, config_instance.key_file)),
#                                     verify=os.path.join(config_instance.cert_path, config_instance.tembita_cert_file))
#
#         else:
#             url = f"http://{config_instance.trembita_host}/signature"
#             logger.info(f"Спроба завантажити ASIC з ШБО з URL: {url} та параметрами: {query_params}")
#             response = requests.get(url, stream=True, params=query_params)
#
#         response.raise_for_status()
#
#         logger.info(f"Успішно отримано відповідь від сервера з кодом: {response.status_code}")
#
#         # Спроба отримати ім'я файлу з заголовку Content-Disposition
#         content_disposition = response.headers.get('Content-Disposition')
#         if content_disposition:
#             # Паттерн для визначення імені файлу
#             filename_match = re.findall('filename="(.+)"', content_disposition)
#             if filename_match:
#                 local_filename = filename_match[0]
#             else:
#                 local_filename = 'downloaded_file.ext'
#         else:
#             # Якщо заголовку немає, використовуємо ім'я за замовчуванням
#             local_filename = 'downloaded_file.ext'
#
#         # Відкриваємо локальний файл в режимі запису байтів
#         with open(f"{asics_dir}/{local_filename}", 'wb') as file:
#             # Проходимо по частинах відповіді і записуємо їх у файл
#             for chunk in response.iter_content(chunk_size=8192):
#                 file.write(chunk)
#         logger.info(f'Файл успішно завантажено та збережено як:  {local_filename}')
#
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Помилка під час завантаження файлу: {e}")
#         raise


def generate_key_cert(key: str, crt: str, path: str):
    # Генерація особистого ключа та сертифіката
    logger.info("Генерація ключа та сертифіката")
    logger.debug(f"Імʼя файлу ключа: {key}, імʼя файлу сертифіката: {crt}, директорія: {path}")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Створення x509 об'єкту для сертифікату
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "UA"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Kyiv"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Kyiv"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "The Best Company"),
        x509.NameAttribute(NameOID.COMMON_NAME, "test.com"),
    ])

    # Створення самопідписаного сертифікату
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Сертифікат буде чинним протягом одного року
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName("test.com")]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Збереження особистого ключа у файл
    key_full_path = os.path.join(path, key)
    try:
        with open(key_full_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        logger.info(f"Ключ збережено у {key_full_path}")

        # Збереження сертифіката у файл
        crt_full_path = os.path.join(path, crt)

        with open(crt_full_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        logger.info(f"Сертифікат збережено у {crt_full_path}")
    except IOError as e:
        logger.error(f"Помилка під час збереження ключа або сертифікату: {e}")
        raise

def create_dir_if_not_exist(dir_path: str):
    # Створення директорії, якщо вона не існує
    logger.info(f"Перевірка існування директорії: {dir_path}")
    if not os.path.exists(dir_path):
        # Створюємо директорію, якщо її немає
        os.makedirs(dir_path)
        logger.info(f"Директорія '{dir_path}' була створена.")
    else:
        logger.info(f"Директорія '{dir_path}' вже існує.")


def get_files_with_metadata(directory):
    # Отримання списку файлів з метаданими у вказаній директорії
    logger.info(f"Отримання метаданих файлів у директорії: {directory}")
    files_metadata = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        creation_time = os.path.getctime(filepath)
        creation_time_str = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
        files_metadata.append({
            'name': filename,
            'creation_time': creation_time_str
        })
    logger.info(f"Метадані файлів отримано: {files_metadata}")
    return files_metadata


def create_person_wsdl_uri(config_instance):

    # Словник з параметрами запиту
    params = {
        'xRoadInstance': config_instance.service_instance,
        'memberClass': config_instance.service_org_type,
        'memberCode': config_instance.service_org_code,
        'subsystemCode': config_instance.service_org_sub,
        'serviceCode': serv_create_person,
#        'serviceVersion': trembita_service_version, # в чьому прикладі не використовуеться версія сервісу
    }

    # Кодуваня параметрів для створення URL
    query_string = urlencode(params)
    wsdl_uri = f"{config_instance.trembita_protocol}://{config_instance.trembita_host}/wsdl?{query_string}"
    return wsdl_uri

def get_person_by_parameter_wsdl_uri(config_instance):
    # Словник з параметрами запиту
    params = {
        'xRoadInstance': config_instance.service_instance,
        'memberClass': config_instance.service_org_type,
        'memberCode': config_instance.service_org_code,
        'subsystemCode': config_instance.service_org_sub,
        'serviceCode': serv_get_person_by_parameter,
        #        'serviceVersion': trembita_service_version, # в чьому прикладі не використовуеться версія сервісу
    }

    # Кодуваня параметрів для створення URL
    query_string = urlencode(params)
    wsdl_uri = f"{config_instance.trembita_protocol}://{config_instance.trembita_host}/wsdl?{query_string}"
    return wsdl_uri

def edit_person_wsdl_uri(config_instance):
    # Словник з параметрами запиту
    params = {
        'xRoadInstance': config_instance.service_instance,
        'memberClass': config_instance.service_org_type,
        'memberCode': config_instance.service_org_code,
        'subsystemCode': config_instance.service_org_sub,
        'serviceCode': serv_edit_person,
        #        'serviceVersion': trembita_service_version, # в чьому прикладі не використовуеться версія сервісу
    }

    # Кодуваня параметрів для створення URL
    query_string = urlencode(params)
    wsdl_uri = f"{config_instance.trembita_protocol}://{config_instance.trembita_host}/wsdl?{query_string}"
    return wsdl_uri

def delete_person_by_unzr_wsdl_uri(config_instance):
    # Словник з параметрами запиту
    params = {
        'xRoadInstance': config_instance.service_instance,
        'memberClass': config_instance.service_org_type,
        'memberCode': config_instance.service_org_code,
        'subsystemCode': config_instance.service_org_sub,
        'serviceCode': serv_delete_person_by_unzr,
        #        'serviceVersion': trembita_service_version, # в чьому прикладі не використовуеться версія сервісу
    }

    # Кодуваня параметрів для створення URL
    query_string = urlencode(params)
    wsdl_uri = f"{config_instance.trembita_protocol}://{config_instance.trembita_host}/wsdl?{query_string}"
    return wsdl_uri

def create_zeep_client(wsdl_url, config_instance):
    session = Session()
    history = HistoryPlugin()

    if config_instance.trembita_protocol == "https":
        # Устанавливаем клиентский сертификат и ключ
        session.cert = (
            os.path.join(config_instance.cert_path, config_instance.cert_file),
            os.path.join(config_instance.cert_path, config_instance.key_file)
        )
        # Устанавливаем CA сертификат для проверки сертификата сервера
        session.verify = os.path.join(config_instance.cert_path, config_instance.tembita_cert_file)

        transport = Transport(session=session)
        settings = Settings(strict=False, xml_huge_tree=True)
        client = Client(wsdl=wsdl_url, transport=transport, settings=settings)
    else:
        #transport = Transport(session=session)
        # Створюємо клієнта
        #client = Client(wsdl=wsdl_url, transport=transport)
        client = Client(wsdl=wsdl_url)

    return client


def serv_req_get_person(parameter: str, value:str, config_instance):
    # Создаем объекты для заголовков SOAP
    wsdl = get_person_by_parameter_wsdl_uri(config_instance)
    client = create_zeep_client(wsdl, config_instance)

    # Получаем типы из WSDL
    XRoadClientIdentifierType = client.get_type('ns3:XRoadClientIdentifierType')
    XRoadServiceIdentifierType = client.get_type('ns3:XRoadServiceIdentifierType')
    SearchParams = client.get_type('ns2:SearchParams')

    # Заполняем заголовок client
    client_header = XRoadClientIdentifierType(
        objectType="SUBSYSTEM",  # укажите значение objectType
        xRoadInstance=f"{config_instance.client_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.client_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.client_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.client_org_sub}"  # укажите значение subsystemCode, если необходимо
    )

    service_header = XRoadServiceIdentifierType(
        objectType="SERVICE",
        xRoadInstance=f"{config_instance.service_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.service_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.service_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.service_org_sub}",  # укажите значение subsystemCode, если необходимо
        serviceCode=serv_get_person_by_parameter,  # укажите значение serviceCode
#        serviceVersion="?"  # укажите значение serviceVersion, если необходимо
    )

    # Указываем параметры запроса
    user_id = config_instance.trembita_user_id  # задайте значение userId
    request_id = str(uuid.uuid4())  # задайте значение id
    protocol_version = "4.0"  # задайте значение protocolVersion

    # Заполняем тело запроса
    params = SearchParams(
        key = parameter,  # укажите ключ
        value = value  # укажите значение
    )

    # Отправка запроса
    response = client.service.get_person_by_parameter(
        params=params,
        _soapheaders={
            "client": client_header,
            "service": service_header,
            "userId":  user_id,
            "id": request_id,
            "protocolVersion": protocol_version
        }
    )
    response_data = serialize_object(response)
    logger.debug(f"Запит завершено успішно, дані отримано: {response_data}")

    if config_instance.trembita_protocol == "https":
        download_asic_from_trembita(request_id, config_instance)

    # Извлекаем только данные о людях для передачи в шаблон
    body_data = response_data['body']['get_person_by_parameterResult']['SpynePersonModel']

    return body_data

def serv_req_create_person(data: dict, config_instance):
    # Создаем объекты для заголовков SOAP
    wsdl = create_person_wsdl_uri(config_instance)
    client = create_zeep_client(wsdl, config_instance)

    # Получаем типы из WSDL
    XRoadClientIdentifierType = client.get_type('ns3:XRoadClientIdentifierType')
    XRoadServiceIdentifierType = client.get_type('ns3:XRoadServiceIdentifierType')
    SpynePersonModel = client.get_type('ns1:SpynePersonModel')

    # Заполняем заголовок client
    client_header = XRoadClientIdentifierType(
        objectType="SUBSYSTEM",  # укажите значение objectType
        xRoadInstance=f"{config_instance.client_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.client_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.client_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.client_org_sub}"  # укажите значение subsystemCode, если необходимо
    )

    service_header = XRoadServiceIdentifierType(
        objectType="SERVICE",
        xRoadInstance=f"{config_instance.service_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.service_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.service_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.service_org_sub}",  # укажите значение subsystemCode, если необходимо
        serviceCode=serv_create_person,  # укажите значение serviceCode
#        serviceVersion="?"  # укажите значение serviceVersion, если необходимо
    )

    # Указываем параметры запроса
    user_id = config_instance.trembita_user_id  # задайте значение userId
    request_id = str(uuid.uuid4())  # задайте значение id
    protocol_version = "4.0"  # задайте значение protocolVersion

    # Создаем объект `SpynePersonModel`
    person_data = SpynePersonModel(
        name = data["name"],
        surname = data["surname"],
        patronym = data["patronym"],
        dateOfBirth = data["dateOfBirth"],
        gender = data["gender"],
        rnokpp = data["rnokpp"],
        passportNumber = data["passportNumber"],
        unzr = data["unzr"],
    )

    # Отправка запроса
    response = client.service.create_person(
         person=person_data,
        _soapheaders={
            "client": client_header,
            "service": service_header,
            "userId":  user_id,
            "id": request_id,
            "protocolVersion": protocol_version
        }
    )

    response_data = serialize_object(response)
    logger.debug(f"Запит завершено успішно, дані отримано: {response_data}")

    if config_instance.trembita_protocol == "https":
        download_asic_from_trembita(request_id, config_instance)


def serv_req_edit_person(data: dict, config_instance):
    wsdl = edit_person_wsdl_uri(config_instance)
    client = create_zeep_client(wsdl, config_instance)

    # Получаем типы из WSDL
    XRoadClientIdentifierType = client.get_type('ns3:XRoadClientIdentifierType')
    XRoadServiceIdentifierType = client.get_type('ns3:XRoadServiceIdentifierType')
    SpynePersonModel = client.get_type('ns1:SpynePersonModel')

    # Заполняем заголовок client
    client_header = XRoadClientIdentifierType(
        objectType="SUBSYSTEM",  # укажите значение objectType
        xRoadInstance=f"{config_instance.client_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.client_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.client_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.client_org_sub}"  # укажите значение subsystemCode, если необходимо
    )

    service_header = XRoadServiceIdentifierType(
        objectType="SERVICE",
        xRoadInstance=f"{config_instance.service_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.service_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.service_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.service_org_sub}",  # укажите значение subsystemCode, если необходимо
        serviceCode=serv_edit_person,  # укажите значение serviceCode
#        serviceVersion="?"  # укажите значение serviceVersion, если необходимо
    )

    # Указываем параметры запроса
    user_id = config_instance.trembita_user_id  # задайте значение userId
    request_id = str(uuid.uuid4())  # задайте значение id
    protocol_version = "4.0"  # задайте значение protocolVersion

    # Создаем объект `SpynePersonModel`
    person_data = SpynePersonModel(
        name = data["name"],
        surname = data["surname"],
        patronym = data["patronym"],
        dateOfBirth = data["dateOfBirth"],
        gender = data["gender"],
        rnokpp = data["rnokpp"],
        passportNumber = data["passportNumber"],
        unzr = data["unzr"],
    )

    # Отправка запроса
    response = client.service.edit_person(
         person=person_data,
        _soapheaders={
            "client": client_header,
            "service": service_header,
            "userId":  user_id,
            "id": request_id,
            "protocolVersion": protocol_version
        }
    )

    response_data = serialize_object(response)
    logger.debug(f"Запит завершено успішно, дані отримано: {response_data}")

    if config_instance.trembita_protocol == "https":
        download_asic_from_trembita(request_id, config_instance)



def serv_req_delete_person(data: dict, config_instance):
    wsdl = delete_person_by_unzr_wsdl_uri(config_instance)
    client = create_zeep_client(wsdl, config_instance)

    # Получаем типы из WSDL
    XRoadClientIdentifierType = client.get_type('ns3:XRoadClientIdentifierType')
    XRoadServiceIdentifierType = client.get_type('ns3:XRoadServiceIdentifierType')

    # Заполняем заголовок client
    client_header = XRoadClientIdentifierType(
        objectType="SUBSYSTEM",  # укажите значение objectType
        xRoadInstance=f"{config_instance.client_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.client_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.client_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.client_org_sub}"  # укажите значение subsystemCode, если необходимо
    )

    service_header = XRoadServiceIdentifierType(
        objectType="SERVICE",
        xRoadInstance=f"{config_instance.service_instance}",  # укажите значение xRoadInstance
        memberClass=f"{config_instance.service_org_type}",  # укажите значение memberClass
        memberCode=f"{config_instance.service_org_code}",  # укажите значение memberCode
        subsystemCode=f"{config_instance.service_org_sub}",  # укажите значение subsystemCode, если необходимо
        serviceCode=serv_delete_person_by_unzr,  # укажите значение serviceCode
#        serviceVersion="?"  # укажите значение serviceVersion, если необходимо
    )

    # Указываем параметры запроса
    user_id = config_instance.trembita_user_id  # задайте значение userId
    request_id = str(uuid.uuid4())  # задайте значение id
    protocol_version = "4.0"  # задайте значение protocolVersion

    # Выполняем SOAP-запрос с заголовками
    response = client.service.delete_person_by_unzr(
        unzr=data["unzr"],
        _soapheaders={
            "client": client_header,
            "service": service_header,
            "userId": user_id,  # Укажите фактическое значение
            "id": request_id,  # Замените на уникальный ID запроса
            "protocolVersion": protocol_version  # Версия протокола
        }
    )

    if config_instance.trembita_protocol == "https":
        download_asic_from_trembita(request_id, config_instance)


    return response