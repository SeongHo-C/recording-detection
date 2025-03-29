import numpy as np
import cv2
import torch
import time
from PyQt5.QtCore import QThread, pyqtSignal
from ultralytics import YOLO


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = False
        self.can_recording = False
        self.recording = False

        self.initialize_camera()

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = YOLO('weights/detect_s.pt')
        self.model.to(self.device)

        self.cv2_prop_enum = {
            "brightness": 10,
            "contrast": 11,
            "saturation": 12,
            "hue": 13,
            "gamma": 22,
            "gain": 14,
            "white_balance_temperature": 45,
            "sharpness": 20,
            "backlight_compensation": 32,
            "white_balance_automatic": 44,
            "exposure_time_absolute": 15,
            "pan_absolute": 33,
            "tilt_absolute": 34,
            "focus_absolute": 28,
            "zoom_absolute": 27,
            "focus_automatic_continuous": 39,
            "auto_exposure": 21
        }

    def initialize_camera(self, width=640, height=480):
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
            print(f'An error occurred while loading the camera: {e}')
            return False

    def run(self):
        self.running = True

        while self.running:
            if self.cap is None or not self.cap.isOpened():
                print('Camera is not connected')
                break

            ret, frame = self.cap.read()

            if not ret:
                print('Not read frame')
                break

            results = self.model(source=frame, verbose=False)

            hornet_detected = False
            for result in results:
                for cls in result.boxes.cls.cpu().numpy():
                    if int(cls) in {0, 1}:
                        hornet_detected = True
                        break
                if hornet_detected:
                    break

            if self.can_recording:
                if hornet_detected and not self.recording:
                    self.initialize_recording(frame)

            annotated_frame = results[0].plot()
            self.change_pixmap_signal.emit(annotated_frame)

            if self.recording:
                self.record_frame(frame)

    def start_recording(self):
        self.can_recording = True

    def initialize_recording(self, first_frame):
        self.recording = True
        self.recording_start_time = time.time()
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        self.output_file = f'recordings/hornet_{timestamp}.mp4'
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(
            self.output_file,
            fourcc,
            90.0,
            (first_frame.shape[1], first_frame.shape[0])
        )
        print(f'Started recording: {self.output_file}')

    def record_frame(self, frame):
        self.out.write(frame)
        if time.time() - self.recording_start_time > 30:
            self.stop_recording()

    def stop_recording(self):
        self.can_recording = False
        self.recording = False
        if hasattr(self, 'out'):
            self.out.release()
        print(f'Stopped recording: {self.output_file}')
        time.sleep(5)

    def start(self):
        self.running = True
        super().start()

    def stop(self):
        self.running = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.wait()  # wait until thread terminates

    def change_resolution(self, width, height):
        self.stop()

        result = self.initialize_camera(width, height)

        if result:
            self.start()
        else:
            print('Failed to change resolution')

    def update_camera_setting(self, name, value):
        prop = self.cv2_prop_enum[name]

        if self.cap is not None and self.cap.isOpened():
            self.cap.set(prop, value)
            # actual_value = self.cap.get(prop)
            # print(f'Camera setting update completed: {name}, {actual_value}')
