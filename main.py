import numpy as np
import sys
import cv2
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTabWidget, QPushButton
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from video_thread import VideoThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()  # call the constructor of the parent class
        self.setWindowTitle('Hornet detection recording')
        self.camera_data = self.load_camera_data()
        self.setup_ui()
        self.setup_video_thread()
        self.setup_connections()

    def load_camera_data(self):
        try:
            with open('camera_data.json', 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f'Error loading camera data: {e}')
            return {}

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet('border: 4px groove gray; border-radius: 5px')
        self.left_layout.addWidget(self.video_label)

        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)

        self.top_layout = QHBoxLayout()
        self.camera_model_combo = QComboBox()
        for camera_model in self.camera_data.keys():
            self.camera_model_combo.addItem(camera_model)

        self.resolution_combo = QComboBox()
        selected_camera_model = self.camera_model_combo.currentText()
        self.resolutions = self.camera_data[selected_camera_model]['resolution']
        for idx, resolution in enumerate(self.resolutions):
            name = resolution['name']
            self.resolution_combo.addItem(name)
            if name == '640 x 480':
                self.resolution_combo.setCurrentIndex(idx)

        self.top_layout.addWidget(QLabel('Camera model:'))
        self.top_layout.addWidget(self.camera_model_combo)
        self.top_layout.addWidget(QLabel('Resolution:'))
        self.top_layout.addWidget(self.resolution_combo)
        self.right_layout.addLayout(self.top_layout)

        self.tabs = QTabWidget()
        self.right_layout.addWidget(self.tabs)

        self.user_tab = QWidget()
        self.tabs.addTab(self.user_tab, 'User Controls')

        self.camera_tab = QWidget()
        self.tabs.addTab(self.camera_tab, 'Camera Controls')

        self.button_layout = QHBoxLayout()
        self.start_button = QPushButton('Recording Start')
        self.stop_button = QPushButton('Recording Stop')
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.right_layout.addLayout(self.button_layout)

        self.main_layout.addWidget(self.left_widget)
        self.main_layout.addWidget(self.right_widget)

    def setup_video_thread(self):
        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_frame)
        self.thread.start()

    def setup_connections(self):
        self.camera_model_combo.currentTextChanged.connect(self.on_camera_model_changed)
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_changed)

        # self.start_button.clicked.connect(self.start_recordeing)
        # self.stop_button.clicked.connect(self.stop_recordeing)

    def on_camera_model_changed(self, camera_model):
        self.resolution_combo.clear()

        if camera_model in self.camera_data:
            self.resolutions = self.camera_data[camera_model]['resolution']
            for resolution in self.resolutions:
                self.resolution_combo.addItem(resolution['name'])

        # self.update_control_tabs(camera_model)

    def on_resolution_changed(self, resolution_name):
        selected_resolution = next(
            (res for res in self.resolutions if res['name'] == resolution_name),
            None
        )

        if selected_resolution:
            width = selected_resolution['width']
            height = selected_resolution['height']

            self.thread.initialize_camera(width, height)
            self.thread.change_resolution(width, height)
            self.video_label.setFixedSize(width, height)

    @pyqtSlot(np.ndarray)
    def update_frame(self, cv_frame):
        qt_frame = self.convert_cv_qt(cv_frame)
        self.video_label.setPixmap(qt_frame)

    def convert_cv_qt(self, cv_frame):
        rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(convert_to_Qt_format)

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
