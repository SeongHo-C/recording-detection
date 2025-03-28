import numpy as np
import cv2
from PyQt5.QtCore import QThread, pyqtSignal


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.cap = None
        self.is_running = False
        self.recording = False
        self.initialize_camera()

    def initialize_camera(self, width=640, height=480):
        if self.cap is not None:
            self.cap.release()

        try:
            self.cap = cv2.VideoCapture(0)

            if not self.cap.isOpened():
                print('Camera is not open')
                return False

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.cap.set(cv2.CAP_PROP_FPS, 90)

            print(
                f'Actual Resolution: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))} x {int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}')
            print(f'Actual FPS: {self.cap.get(cv2.CAP_PROP_FPS)}')
            return True
        except Exception as e:
            print(f'An error occurred while loading: {e}')
            return False

    def run(self):
        self.is_running = True

        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                print('Camera is not connected')
                break

            ret, frame = self.cap.read()

            if not ret:
                print('Could not read frame')
                break

            self.change_pixmap_signal.emit(frame)

    def start(self):
        self.is_running = True
        super().start()

    def stop(self):
        self.is_running = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.wait()  # wait until thread terminates
