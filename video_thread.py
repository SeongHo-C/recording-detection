import numpy as np
import cv2
from PyQt5.QtCore import QThread, pyqtSignal


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.initialize_camera()

        self.running = False
        self.recording = False

    def initialize_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        self.cap.set(cv2.CAP_PROP_FPS, 60)

        print(f'Actual FPS: {self.cap.get(cv2.CAP_PROP_FPS)}')

    def run(self):
        self.running = True

        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.change_pixmap_signal.emit(frame)

    def start(self):
        self.running = True
        super().start()

    def stop(self):
        self.running = False
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        self.wait()  # wait until thread terminates
