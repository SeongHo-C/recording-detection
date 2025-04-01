import numpy as np
import sys
import cv2
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTabWidget, QPushButton, QFormLayout, QSlider, QCheckBox
from PyQt5.QtCore import Qt, pyqtSlot, QTimer
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

        self.recording_label = QLabel()
        self.recording_label.setText('Current State: <span style="color: blue">WAITING</span>')
        self.recording_label.setAlignment(Qt.AlignVCenter)
        self.left_layout.addWidget(self.recording_label, 0, Qt.AlignTop | Qt.AlignLeft)

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
        self.camera_model = self.camera_model_combo.currentText()
        self.resolutions = self.camera_data[self.camera_model]['resolution']
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
        self.user_tab_layout = QFormLayout(self.user_tab)
        self.tabs.addTab(self.user_tab, 'User Controls')

        self.camera_tab = QWidget()
        self.camera_tab_layout = QFormLayout(self.camera_tab)
        self.tabs.addTab(self.camera_tab, 'Camera Controls')

        self.update_control_tabs()

        self.default_setting_button = QPushButton('Default Setting')
        self.right_layout.addWidget(self.default_setting_button)

        self.button_layout = QHBoxLayout()
        self.start_button = QPushButton('Detecting Start')
        self.stop_button = QPushButton('Detecting Stop')
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

        self.default_setting_button.clicked.connect(self.apply_default_settings)
        self.start_button.clicked.connect(self.on_start_recording)
        self.stop_button.clicked.connect(self.on_stop_recording)

    def on_camera_model_changed(self, camera_model):
        self.resolution_combo.clear()
        self.camera_model = camera_model

        if camera_model in self.camera_data:
            self.resolutions = self.camera_data[self.camera_model]['resolution']
            for resolution in self.resolutions:
                self.resolution_combo.addItem(resolution['name'])

            self.update_control_tabs()

    def update_control_tabs(self):
        self.clear_layout(self.user_tab_layout)
        self.clear_layout(self.camera_tab_layout)

        if self.camera_model in self.camera_data:
            properties = self.camera_data[self.camera_model]['properties']

            if 'User Controls' in properties:
                for control in properties['User Controls']:
                    self.add_control_widget(self.user_tab_layout, control)

            if 'Camera Controls' in properties:
                for control in properties['Camera Controls']:
                    self.add_control_widget(self.camera_tab_layout, control)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                if item.layout() is not None:
                    self.clear_layout(item.layout())

    def add_control_widget(self, layout, control):
        name = control['name']
        control_type = control.get('type', '')

        if control_type == 'int':
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(control['min'])
            slider.setMaximum(control['max'])
            slider.setValue(control['value'])
            slider.setTickInterval(control['step'])

            value_label = QLabel(str(control['value']))

            debounce_timer = QTimer()
            debounce_timer.setInterval(300)
            debounce_timer.setSingleShot(True)

            debounce_timer.timeout.connect(lambda: self.update_camera_setting(control_type, name, slider.value()))

            slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
            slider.valueChanged.connect(lambda: debounce_timer.start())

            slider_layout = QHBoxLayout()
            slider_layout.addWidget(slider)
            slider_layout.addWidget(value_label)

            layout.addRow(name, slider_layout)
        elif control_type == 'bool':
            checkbox = QCheckBox()
            checkbox.setChecked(control['value'] == 1)

            checkbox.stateChanged.connect(lambda state: self.update_camera_setting(control_type, name, state))

            layout.addRow(name, checkbox)
        elif control_type == 'menu':
            combo = QComboBox()
            if 'menu' in control:
                for key, value in control['menu'].items():
                    combo.addItem(value, key)

                for i in range(combo.count()):
                    if combo.itemData(i) == str(control['value']):
                        combo.setCurrentIndex(i)
                        break

                combo.currentIndexChanged.connect(
                    lambda index: self.update_camera_setting(control_type, name, int(combo.itemData(index))))

            layout.addRow(name, combo)

    def update_camera_setting(self, type, name, value):
        if type == 'bool':
            value = 1 if value == 2 else 0

        result = self.thread.update_camera_setting(name, value)
        if result:
            properties = self.camera_data[self.camera_model]['properties']
            for control_group in properties.values():
                for control in control_group:
                    if control['name'] == name:
                        control['value'] = value
                        break

    def apply_default_settings(self):
        if self.camera_model in self.camera_data:
            properties = self.camera_data[self.camera_model]['properties']

            for group_name, controls in properties.items():
                for control in controls:
                    default_value = control.get('default', control['value'])
                    control['value'] = default_value

                    self.thread.update_camera_setting(control['name'], default_value)

            self.update_control_tabs()

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

    def on_start_recording(self):
        self.recording_label.setText('Current State: <span style="color: red">DETECTING</span>')
        self.thread.start_recording()

    def on_stop_recording(self):
        self.recording_label.setText('Current State: <span style="color: blue">WAITING</span>')
        self.thread.stop_recording()

    def save_camera_data(self):
        try:
            with open('camera_data.json', 'w', encoding='utf-8') as file:
                json.dump(self.camera_data, file, indent=4)
                print('Camera data saved to JSON file')
        except Exception as e:
            print(f'Error saving camera data: {e}')

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
        self.save_camera_data()
        self.thread.stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
