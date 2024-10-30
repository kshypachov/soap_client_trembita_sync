from csv import excel

from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
from flask_bootstrap import Bootstrap
import logging
import utils
import sys
import os


# Зчитування параметрів додатку з конфігураційного файлу
conf = utils.Config('config.ini')

# Налаштування логування
try:
    utils.configure_logging(conf)
    logger = logging.getLogger(__name__)
    logger.info("Логування налаштовано успішно.")
except Exception as e:
    # Якщо виникає помилка при налаштуванні логування, додаток припиняє роботу
    print(f"Помилка налаштування логування: {e}")
    sys.exit(1)

logger.debug("Початок ініціалізації додатку")

# Ініціалізація директорій для сертифікатів та ASIC файлів
crt_directory = conf.cert_path
asic_directory = conf.asic_path
key = conf.key_file
cert = conf.cert_file

# Створення директорій для сертифікатів і ASIC, якщо їх не існує
utils.create_dir_if_not_exist(crt_directory)
utils.create_dir_if_not_exist(asic_directory)

# Шляхи до ключів і сертифікатів
private_key_full_path = os.path.join(crt_directory, key)
certificate_full_path = os.path.join(crt_directory, cert)

# Якщо ключ або сертифікат не знайдені, генеруємо їх
if not os.path.exists(private_key_full_path) or not os.path.exists(certificate_full_path):
    logger.info(f"Не знайдено ключ: {key} або сертифікат {cert} у директорії {crt_directory}")
    utils.generate_key_cert(key, cert, crt_directory)


# Ініціалізація додатку Flask
app = Flask(__name__)
Bootstrap(app)
logger.info("Додаток Flask ініціалізовано.")

#service_create_person_wsdl_uri           = "http://10.0.20.235/wsdl?xRoadInstance=test1&memberClass=GOV&memberCode=10000004&subsystemCode=SUB_SERVICE&serviceCode=create_person"
#service_get_person_by_parameter_wsdl_uri = "http://10.0.20.235/wsdl?xRoadInstance=test1&memberClass=GOV&memberCode=10000004&subsystemCode=SUB_SERVICE&serviceCode=get_person_by_parameter"
#service_edit_person_wsdl_uri             = "http://10.0.20.235/wsdl?xRoadInstance=test1&memberClass=GOV&memberCode=10000004&subsystemCode=SUB_SERVICE&serviceCode=edit_person"
#service_delete_person_by_unzr_wsdl_uri   = "http://10.0.20.235/wsdl?xRoadInstance=test1&memberClass=GOV&memberCode=10000004&subsystemCode=SUB_SERVICE&serviceCode=delete_person_by_unzr"



@app.route('/', methods=['GET', 'POST'])
def search_user():
    logger.debug(f"Отримано {'POST' if request.method == 'POST' else 'GET'} запит на маршрут '/'.")
    if request.method == 'POST':  # Якщо прийшов POST-запит, обробляємо форму пошуку користувача
        search_field = request.form.get('search_field')
        search_value = request.form.get('search_value')

        logger.debug(f"Отримано параметри пошуку: {search_field} : {search_value} ")

        try:
            # Запит на отримання інформації про користувача
            response = utils.serv_req_get_person(search_field, search_value, conf)
        except Exception as e:
            # У разі помилки відправляємо повідомлення про помилку на сторінку
            logger.error(f"Виникла помилка: {str(e)}")
            return render_template('error.html', error_message=e, current_page='index')
        return render_template('list_person.html', data=response, current_page='index')

    # Якщо запит GET, просто віддаємо вебсторінку з формою пошуку
    return render_template('search_form.html',  current_page='index') # Прийшов GET запит, просто віддаємо вебсторінку

# Обробка створення нового користувача
@app.route('/create', methods=['GET', 'POST'])
def create_user():
    logger.debug(f"Отримано {'POST' if request.method == 'POST' else 'GET'} запит на маршрут '/create'.")
    if request.method == 'POST':  # Якщо прийшов POST-запит, обробляємо створення нового користувача
        try:
            form_data = request.get_json()  # Зчитуємо дані з форми
            logger.debug(f"Отримано запит на створення з параметрами: {form_data}")
            # Викликаємо функцію для додавання нового користувача
            response = utils.serv_req_create_person(form_data, conf)
            resp = jsonify(message=response), 200
            return resp
        except Exception as e:
            logger.debug(f"Виникла помилка: {str(e)}")
            resp = jsonify(message=f'Помилка при створенні об’єкта користувача: {str(e)}'), 422
            return resp

    # Якщо запит GET, просто віддаємо вебсторінку з формою для створення користувача
    return render_template('create_person.html', current_page='create')  # Прийшов GET запит, просто віддаємо вебсторінку

# Обробка редагування даних користувача
@app.route('/edit', methods = ['POST'])
def edit_user():
    logger.debug("Отримано POST запит на маршрут '/edit'.")
    data = request.get_json() # Отримуємо дані для редагування
    logger.debug(f"Отримано дані для редагування: {data}")
    try:
        # Викликаємо функцію для редагування даних користувача
        response = utils.serv_req_edit_person(data, conf)
    except Exception as e:
        logger.error(f"Виникла помилка: {str(e)}")
        resp = jsonify(message=f"Виникла помилка при обробці запиту на редагування: error: {str(e)}"), 500
        return resp
    return jsonify(message=response), 200


# Обробка видалення користувача
@app.route('/delete', methods = ['POST'])
def delete_person():
    logger.debug("Отримано POST запит на маршрут '/delete'.")
    data = request.get_json()   # Отримуємо дані про користувача для видалення
    logger.debug(f"Отримано запит на видалення: {data}")
    try:
        # Викликаємо функцію для видалення користувача
        http_resp = utils.serv_req_delete_person(data, conf)
    except Exception as e:
        logger.error(f"Виникла помилка: {str(e)}")
        resp = jsonify(message=f"Виникла помилка при обробці запиту на видалення: error: {str(e)}"), 500
        return resp
    return jsonify(message= http_resp.body), 200


# Обробка відображення списку файлів
@app.route('/files')
def list_files():
    logger.debug("Отримано GET запит на маршрут '/files'.")
    try:
        # Отримуємо список файлів у ASIC директорії
        files = []
        for filename in os.listdir(asic_directory):
            filepath = os.path.join(asic_directory, filename)
            if os.path.isfile(filepath):
                creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
                files.append({
                    'name': filename,
                    'creation_time': creation_time.strftime('%Y-%m-%d %H:%M:%S')
                })

        # Сортуємо файли за датою створення в порядку спадання
        files = sorted(files, key=lambda x: x['creation_time'], reverse=True)
        logger.debug("Список файлів отримано успішно.")

        return render_template('list_files_run_away.html', files=files, current_page='files')
    except Exception as e:
        logger.error(f"Виникла помилка: {str(e)}")
        return render_template('error.html', error_message=e, current_page='files')

# Обробка відображення списку сертифікатів
@app.route('/certs')
def list_certs():
    logger.debug("Отримано GET запит на маршрут '/certs'.")
    try:
        # Отримуємо список сертифікатів у директорії
        files = []
        for filename in os.listdir(crt_directory):
            filepath = os.path.join(crt_directory, filename)
            if os.path.isfile(filepath):
                creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
                files.append({
                    'name': filename,
                    'creation_time': creation_time.strftime('%Y-%m-%d %H:%M:%S')
                })

        # Сортуємо сертифікати за датою створення в порядку спадання
        files = sorted(files, key=lambda x: x['creation_time'], reverse=True)
        logger.debug("Список сертифікатів отримано успішно.")

        return render_template('list_certs.html', files=files, current_page='certs')
    except Exception as e:
        logger.error(f"Виникла помилка: {str(e)}")
        return render_template('error.html', error_message=e, current_page='certs')

# Завантаження сертифікату
@app.route('/download_cert/<filename>')
def download_cert(filename):
    logger.debug(f"Отримано GET запит на маршрут '/download_cert/{filename}'.")
    CERT_DIR = os.path.join(os.getcwd(), crt_directory)
    safe_filename = os.path.basename(filename)  # Валідація імені файлу для безпеки
    try:
        return send_from_directory(CERT_DIR, safe_filename, as_attachment=True) # Відправка сертифікату
    except Exception as e:
        logger.error(f"Виникла помилка: {str(e)}")
        return render_template('error.html', error_message=e, current_page='certs')



if __name__ == '__main__':
    # Запуск додатку Flask з режимом налагодження (debug)
    logger.info("Запуск додатку Flask.")
    app.run(debug=True)
    logger.info("Додаток Flask зупинено.")

