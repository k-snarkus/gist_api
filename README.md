#!/usr/bin/env python3
# gist_api

# gist_api 
# скрипиты для автоматического создания интерфейсов сетевого оборудования по заданным параметрам
# для работы, помимо стандартных, используется библиотека pymysqlm.
# также  потребуется любой интерпретатор python =)
# секретные данные (учетка для оборудования и данные БД) хранятся отдельно и в публичный доступ разумеется не выкладываются)
#
# логика работы:
# по id модуля получает информацию о линковых /30 и клиентских адресах;
# проверяет по базе существующих маршрутов наличие данных сетей на других узлах, при обнаружении - подключается, удаляет.
# далее подключается к заданному узлу, для существующих интерфейсов добавляет адреса, для новых - создает полностью.
# Если линковая сеть задана - она прописывается на саб, клиентские добавляются статикой.
# Если линковая сеть не задана - все клиентские адреса добавляются на интерфейс.
#
# скрипт l3_routes действует аналогично, но все сети прописывает статикой на l3vpn ТТК.
#
#
# If you are not a CIT RT employee, this code seems to be useless for you.
# However, you can use any parts of code to interact with the networking devices
