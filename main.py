import math
import sys
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QInputDialog, QPushButton, \
    QComboBox, QCheckBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from urllib3.util.retry import Retry


def get_response(url, params):
    session = requests.Session()
    retry = Retry(total=10, connect=5)
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session.get(url, params=params)


class MyComboBox(QComboBox):
    def __init__(self, parent):
        self.parent = parent
        super(MyComboBox, self).__init__()

    def keyPressEvent(self, event):
        self.parent.keyPressEvent(event)


class Map(QLabel):
    def __init__(self, app):
        super(Map, self).__init__()
        self.app = app

    def mousePressEvent(self, event):
        d = 2 ** self.app.map_z
        image_width, image_height = self.app.map_size
        lon_center, lat_center = self.app.map_ll

        lon_per_pix = 360 / 250 / d
        lon = lon_center + (event.x() - image_width / 2) * lon_per_pix
        if lon < -180:
            lon %= 180
        elif lon > 180:
            lon = -180 + lon % 180
        k = self.get_k_of_click(event.y(), lat_center, image_height, d)
        if k is not None:
            lat = self.get_lat(k)
            self.app.set_pending_by_coords(lon, lat, False)

    def get_lat(self, k):  # Gudermannian function
        return math.degrees(math.atan(math.sinh(k)))

    def get_k(self, lat):  # inverse Gudermannian function
        return math.asinh(math.tan(math.radians(lat)))

    def get_k_of_click(self, y_cursor, lat_center, image_height, d):
        k_max = self.get_k(85)
        k_min = self.get_k(-85)
        coeff = 250 / (k_max - k_min) * d
        k_center = self.get_k(lat_center)
        y_min = image_height / 2 - (k_max - k_center) * coeff
        y_max = image_height / 2 + (k_center - k_min) * coeff
        if y_min <= y_cursor <= y_max:
            k = k_center + (image_height / 2 - y_cursor) / coeff
            return k


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.map_ll = [0, 0]
        self.map_l = 'map'
        self.API_KEY = '40d1649f-0493-4b70-98ba-98533de7710b'
        self.map_z = 1
        self.map_size = [650, 450]
        self.map_pt = None
        self.toponym = None
        self.delta = 30
        self.initUI()
        self.refresh_map()

    def initUI(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        self.layout = QVBoxLayout(cw)

        #############################################################################################################
        # переключатель слоёв карты (схема/спутник/гибрид), при изменении которого надо менять вид карты
        self.change_view_combo_box = MyComboBox(self)
        self.change_view_combo_box.addItem('схема')
        self.change_view_combo_box.addItem('спутник')
        self.change_view_combo_box.addItem('гибрид')
        self.layout.addWidget(self.change_view_combo_box)
        self.change_view_combo_box.currentIndexChanged.connect(self.change_map_view)
        #############################################################################################################

        #############################################################################################################
        # виджет, в котором показывается изображение карты
        self.map = Map(self)
        self.layout.addWidget(self.map)
        #############################################################################################################

        #############################################################################################################
        # конпка для того, чтобы найти географический объект
        self.find_btn = QPushButton(self)
        self.find_btn.setText('Найти')
        self.layout.addWidget(self.find_btn)
        self.find_txt = None
        self.find_btn.clicked.connect(self.finding)
        #############################################################################################################

        #############################################################################################################
        # виджет, где будет показываться полный адрес найденного географического объекта
        self.label_for_address = QLabel()
        self.layout.addWidget(self.label_for_address)
        #############################################################################################################

        #############################################################################################################
        # конпка для того, чтобы сбросить найденный географический объект
        self.delete_btn = QPushButton(self)
        self.layout.addWidget(self.delete_btn)
        self.delete_btn.setText('Удалить метку')
        self.delete_btn.clicked.connect(self.deleting)
        # при нажатии конпки - удалить полный адрес найденного гегографического объекта с экрана
        self.delete_btn.clicked.connect(lambda: self.label_for_address.setText(''))
        #############################################################################################################

        self.show_postal_index = QCheckBox()
        self.layout.addWidget(self.show_postal_index)
        self.show_postal_index.clicked.connect(self.update_postal_index)
        self.update_postal_index()

    def deleting(self):
        self.map_pt = None
        self.toponym = None
        self.refresh_map()
        self.update_postal_index()

    def update_postal_index(self):
        index_cb_text = 'Показывать почтовый индекс'
        address_label_text = self.get_address(self.toponym)
        if self.toponym:
            address_obj = self.toponym['metaDataProperty']['GeocoderMetaData']['Address']
            postal_ind = address_obj['postal_code'] if 'postal_code' in address_obj else None
            disabled = not postal_ind
            address = self.get_address(self.toponym)
            if postal_ind:
                if self.show_postal_index.isChecked():
                    postal_ind = '\nПочтовый индекс: ' + postal_ind
                    address_label_text += postal_ind
            else:
                index_cb_text += ' (у данного объекта нет почтового индекса)'
        else:
            index_cb_text += ' (объект не указан)'
            disabled = True
        self.show_postal_index.setText(index_cb_text)
        self.label_for_address.setText(address_label_text)
        self.show_postal_index.setDisabled(disabled)

    def change_map_view(self):
        view = self.change_view_combo_box.currentText()
        if view == 'схема':
            self.map_l = 'map'
        elif view == 'спутник':
            self.map_l = 'sat'
        elif view == 'гибрид':
            self.map_l = 'sat,skl'
        self.refresh_map()

    def geocode_by_address(self, address):
        url = 'http://geocode-maps.yandex.ru/1.x'
        params = {'apikey': self.API_KEY, 'geocode': address, 'format': 'json'}
        response = get_response(url, params)
        if response:
            json_response = response.json()
        else:
            raise RuntimeError('Ошибка выполнения запроса')
        features = json_response['response']["GeoObjectCollection"]["featureMember"]
        return features[0]['GeoObject'] if features else None

    def finding(self):
        name, ok_pressed = QInputDialog.getText(self, "Введите название", 'Введите название места:')
        if ok_pressed:
            self.find_txt = name
            self.set_pending_by_address(name)

    def set_pending(self, toponym, lon, lat, change_ll):
        if toponym:
            self.toponym = toponym
            if change_ll:
                self.map_ll = [lon, lat]
            self.map_pt = f'{lon},{lat},round'
            self.refresh_map()
            self.show_address(toponym)
            self.update_postal_index()

    def set_pending_by_address(self, address, change_ll=True):
        toponym = self.geocode_by_address(address)
        if toponym:
            lon, lat = map(float, toponym['Point']["pos"].split())
            self.set_pending(toponym, lon, lat, change_ll)

    def set_pending_by_coords(self, lon, lat, change_ll=True):
        self.set_pending(self.geocode_by_coords(f'{lon},{lat}'), lon, lat, change_ll)

    def geocode_by_coords(self, coords):
        params = {"apikey": "40d1649f-0493-4b70-98ba-98533de7710b", "geocode": coords, "format": "json"}
        resp = get_response("http://geocode-maps.yandex.ru/1.x/", params).json()
        if resp:
            return resp["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]

    # Показывает полный адрес найденного географического объекта в виджете

    def get_address(self, toponym):
        return toponym['metaDataProperty']['GeocoderMetaData']['text'] if toponym else ''

    def show_address(self, toponym):
        self.label_for_address.setText(self.get_address(toponym))

    def refresh_map(self):
        x, y = self.map_ll
        w, h = self.map_size
        params = {'ll': f'{x},{y}', 'l': self.map_l, 'apikey': self.API_KEY, 'z': self.map_z, 'size': f'{w},{h}'}
        if self.map_pt:
            params['pt'] = self.map_pt
        resp = get_response('https://static-maps.yandex.ru/1.x/', params)
        with open('tmp.png', 'wb') as f:
            f.write(resp.content)
        self.map.setPixmap(QPixmap('tmp.png'))

    def keyPressEvent(self, event):
        k = event.key()
        min_z = 0 if min(self.map_size) <= 250 else 1
        if k == Qt.Key_PageUp and self.map_z < 17:
            self.map_z += 1
            self.delta /= 2
        if k == Qt.Key_PageDown and self.map_z > min_z:
            self.map_z -= 1
            self.delta *= 2
        if (k == Qt.Key_A or k == 1060) and self.map_ll[0] - self.delta >= -180:
            self.map_ll[0] -= self.delta
        if (k == Qt.Key_D or k == 1042) and self.map_ll[0] + self.delta <= 180:
            self.map_ll[0] += self.delta
        if (k == Qt.Key_W or k == 1062) and self.map_ll[1] + self.delta <= 80:
            self.map_ll[1] += self.delta
        if (k == Qt.Key_S or k == 1067) and self.map_ll[1] - self.delta >= -80:
            self.map_ll[1] -= self.delta
        self.refresh_map()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
