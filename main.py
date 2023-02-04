import sys
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QInputDialog, QPushButton, \
    QComboBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from urllib3.util.retry import Retry


class MyComboBox(QComboBox):
    def __init__(self, parent):
        self.parent = parent
        super(MyComboBox, self).__init__()

    def keyPressEvent(self, event):
        self.parent.keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()
        self.map_ll = [50, 50]
        self.map_l = 'map'
        self.API_KEY = '40d1649f-0493-4b70-98ba-98533de7710b'
        self.map_z = 3
        self.delta = 10
        self.refresh_map()

    def initUI(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        self.setGeometry(500, 500, 500, 500)
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
        self.map = QLabel()
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

    def deleting(self):
        try:
            self.ping = False
            self.refresh_map()
        except Exception:
            pass

    def change_map_view(self):
        view = self.change_view_combo_box.currentText()
        if view == 'схема':
            self.map_l = 'map'
        elif view == 'спутник':
            self.map_l = 'sat'
        elif view == 'гибрид':
            self.map_l = 'sat,skl'
        self.refresh_map()

    def geocode(self, adress):
        geocoder_req = f"http://geocode-maps.yandex.ru/1.x/?apikey={self.API_KEY}" \
                       f"&geocode={adress}&format=json"
        response = requests.get(geocoder_req)
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
            new_ll = self.get_address_coords(name).split()
            self.map_ll = [float(new_ll[0]), float(new_ll[1])]
            self.ping = True
            self.pt = ','.join(map(str, self.map_ll)) + f',pmwtm'
            self.refresh_map()

    def get_address_coords(self, address):
        toponym = self.geocode(address)

        # Показать полный адрес найденного географического объекта на экране
        self.show_address(toponym)

        toponym_coordinates = toponym['Point']["pos"]
        return toponym_coordinates

    # Показывает полный адрес найденного географического объекта в виджете
    def show_address(self, toponym):
        full_address = toponym['metaDataProperty']['GeocoderMetaData']['text']
        self.label_for_address.setText(full_address)

    def refresh_map(self):
        try:
            if self.ping:
                params = {'ll': ','.join(map(str, self.map_ll)), 'l': self.map_l, 'apikey': self.API_KEY,
                          'z': self.map_z, 'pt': self.pt}
            else:
                params = {'ll': ','.join(map(str, self.map_ll)), 'l': self.map_l, 'apikey': self.API_KEY,
                          'z': self.map_z}
        except Exception:
            params = {'ll': ','.join(map(str, self.map_ll)), 'l': self.map_l, 'apikey': self.API_KEY,
                      'z': self.map_z}
        session = requests.Session()
        retry = Retry(total=10, connect=5)
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        resp = session.get('https://static-maps.yandex.ru/1.x/', params=params)
        with open('tmp.png', 'wb') as f:
            f.write(resp.content)
        self.map.setPixmap(QPixmap('tmp.png'))

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key_PageUp and self.map_z < 17:
            self.map_z += 1
        if k == Qt.Key_PageDown and self.map_z > 0:
            self.map_z -= 1
        if k == Qt.Key_A or k == 1060 and self.map_ll[0] - self.delta >= -180:
            self.map_ll[0] -= self.delta
        if k == Qt.Key_D or k == 1042 and self.map_ll[0] + self.delta <= 180:
            self.map_ll[0] += self.delta
        if k == Qt.Key_W or k == 1062 and self.map_ll[1] + self.delta <= 80:
            self.map_ll[1] += self.delta
        if k == Qt.Key_S or k == 1067 and self.map_ll[1] - self.delta >= -80:
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
