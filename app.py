from flask import Flask, render_template, request, jsonify, send_from_directory
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
            print(response)
        except Exception as e:
            # У разі помилки відправляємо повідомлення про помилку на сторінку
            logger.error(f"Виникла помилка: {str(e)}")
            return render_template('error.html', error_message=e, current_page='index')
        return render_template('list_person.html', data=response, current_page='index')

    # Якщо запит GET, просто віддаємо вебсторінку з формою пошуку
    return render_template('search_form.html',  current_page='index') # Прийшов GET запит, просто віддаємо вебсторінку



if __name__ == '__main__':
    # Запуск додатку Flask з режимом налагодження (debug)
    logger.info("Запуск додатку Flask.")
    app.run(debug=True)
    logger.info("Додаток Flask зупинено.")

