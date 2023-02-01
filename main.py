import sys
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from urllib3.util.retry import Retry


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()
        self.map_ll = [50, 50]
        self.map_l = 'map'
        self.map_key = ''
        self.map_z = 3
        self.delta = 10
        self.refresh_map()

    def initUI(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        self.setGeometry(500, 500, 500, 500)
        lt = QVBoxLayout(cw)
        self.map = QLabel()
        lt.addWidget(self.map)

    def refresh_map(self):
        params = {'ll': ','.join(map(str, self.map_ll)), 'l': self.map_l, 'apikey': self.map_key, 'z': self.map_z}
        session = requests.Session()
        retry = Retry(total=10, connect=5)
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('http://', adapter)
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
        if k == Qt.Key_Left and self.map_ll[0] - self.delta >= -180:
            self.map_ll[0] -= self.delta
        if k == Qt.Key_Right and self.map_ll[0] + self.delta <= 180:
            self.map_ll[0] += self.delta
        if k == Qt.Key_Up and self.map_ll[1] + self.delta <= 80:
            self.map_ll[1] += self.delta
        if k == Qt.Key_Down and self.map_ll[1] - self.delta >= -80:
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
