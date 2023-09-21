import math
import time
import torch
import platform
import cv2
import cvzone
from torch import mps
from device import Device
from logger import Logger
from ultralytics import YOLO
from datetime import datetime, timedelta
from memory_profiler import profile
from test import AccuracyCalculator


class System:

    def __init__(self, url, timestamp, logger: Logger, surveillance_name:str):
        self.acceleration_type = self.populate_architecture()
        self.operating_device = Device(surveillance_name, 2)
        self.cap = self.get_cam_type("recording", url)
        self.model = self.get_model()
        self.className = self.get_classname()
        self.fps = self.get_fps()
        self.frame_no = 1
        self.play = True
        self.timestamp = timestamp
        self.logger = logger

    @staticmethod
    def populate_architecture():
        # Check Architecture is arm64 or x86
        if platform.mac_ver()[2] == "arm64":
            # this ensures that:
            #   - MacOS version is at least 12.3+
            #   - PyTorch installation was built with MPS activated.
            if torch.backends.mps.is_available() and torch.backends.mps.is_built():
                return "mps"
            else:
                return "cpu"
        else:
            if torch.cuda.is_available():
                return 'cuda'

    @staticmethod
    def empty_gpu_cache():
        if platform.mac_ver()[2] == "arm64" and torch.backends.mps.is_available():
            mps.empty_cache()
        else:
            torch.cuda.empty_cache()

    @staticmethod
    def get_cam_type(cam_type: str, video_url: str):
        if cam_type == "live":
            # For Webcam
            return cv2.VideoCapture(1)
        if cam_type == "recording":
            # For video feed
            return cv2.VideoCapture(video_url)  # For Video

    @staticmethod
    def get_model():
        model = YOLO("../Yolo-Weights/yolov8x.pt")
        return model

    @staticmethod
    def get_classname():
        return [
            "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
            "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
            "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
            "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
            "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
            "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
            "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "potted plant", "bed",
            "dining table", "toilet", "tv monitor", "laptop", "mouse", "remote", "keyboard", "cell phone",
            "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
            "teddy bear", "hair drier", "toothbrush", "coin", "watch", "fan"
        ]

    def set_initial_frame_count(self, starting_frame: int):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, starting_frame)

    #@profile()
    def run_video_scan(self, initial_frame_count, unprocessed_second=None, object_id=0):

        # Singleton Accuracy Calculator
        accuracy_calculator = AccuracyCalculator()

        # Check if incoming id is:
        #   0 - suggesting that new feed with no knowledge of model to choose
        #   > 0 - suggesting new feed with known knowledge of model to choose
        current_suggested_id = object_id

        # Check if video needs to skip to particular point
        if initial_frame_count is not None:
            self.set_initial_frame_count(int(initial_frame_count))

        if unprocessed_second is not None:
            print(self.get_fps() * unprocessed_second)
            self.set_initial_frame_count(int(self.get_fps() * unprocessed_second))

        while True:

            # Start reading frames from video
            success, img = self.cap.read()
            # Track each frame with YOLOv8 detection and segmentation
            results = self.model.track(source=img, tracker='bytetrack.yaml', persist=True, stream=True,
                                       device=self.acceleration_type)

            # Total number of objects identified
            for r in results:

                # Get all contours
                boxes = r.boxes

                # create new array for temporary checking of out of frame objects
                current_frame_centroid = []

                for box in boxes:

                    # Check if id exist from box
                    if box.id is not None:

                        # Retrieve object id
                        id = box.id.cpu().numpy().astype(int)

                        # Store id if 1 person detected
                        if current_suggested_id == 0:
                            total_person_detected = [box for box in boxes if
                                                     self.className[int(box.cls[0])] == 'person']
                            if len(total_person_detected) == 1:
                                current_suggested_id = total_person_detected[0].id.cpu().numpy().astype(int)

                        # Check if object class == person
                        # and id == int(object_id)
                        if self.className[int(box.cls[0])] == 'person' and int(id) == int(current_suggested_id):

                            # check for confidence score above 0.8 only
                            if (math.ceil((box.conf[0] * 100)) / 100) > 0.75:

                                # append new frame object to current_frame_object and draw person bounding boxes
                                centroid_new, id = self.operating_device.draw_bounding_boxes(id, box, self.className,
                                                                                             img)
                                accuracy_calculator.set_detected_frames()

                                # Append object centroid into the current_frame_object list
                                current_frame_centroid.append([id, centroid_new])

                        # Draw frame counts on screen
                        cvzone.putTextRect(img, str(self.cap.get(cv2.CAP_PROP_POS_FRAMES)), (1800, 35), scale=2,
                                           thickness=1)

                # Skip 4 frames per check
                if self.frame_no % 4 == 0:

                    # Check all the existing objects and new objects
                    self.operating_device.check_object_addition_or_updates(current_frame_centroid,
                                                                           self.operating_device.objects, self.logger)

                    # Check out of frame objects
                    movement_angle = self.operating_device.check_out_of_frame(self.operating_device.objects,
                                                                              current_frame_centroid, object_id)

                    print("Last moved angle: ", movement_angle)

                    # Check if out of frame
                    if movement_angle is not None:
                        print("Checking if id exist")
                        new_surveillance = self.operating_device.get_next_camera_id(movement_angle)

                        # Check if surveillance ended
                        if new_surveillance is None:
                            return None
                        else:
                            new_time = self.get_transition_timeframe()

                            # DEBUGGING LOG
                            # Show object out of frame result
                            print("Object out of frame")
                            print("Replacing Surveillance: ", new_surveillance)
                            print("Handover time: ", new_time)

                            self.logger.write_report("text", "Object out of frame, Replacing Surveillance: " + str(new_surveillance) + "Handover time: " + str(new_time))
                            self.logger.write_report("page_break", "")

                            return {"surveillance": new_surveillance, 'timestamp': new_time, 'frame': self.frame_no}

            self.frame_no += 1
            accuracy_calculator.set_total_frames()
            cv2.imshow("Image", img),
            cv2.waitKey(1)

    def disposed_data(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def get_fps(self):
        return self.cap.get(cv2.CAP_PROP_FPS)

    @profile()
    def get_transition_timeframe(self):
        # Convert string to datetime object
        dt = datetime.fromtimestamp(int(self.timestamp))
        datetime_result = (dt + timedelta(milliseconds=(int(self.cap.get(cv2.CAP_PROP_POS_MSEC))))).replace(microsecond=0)
        unix_timestamp = time.mktime(datetime_result.timetuple())

        # DEBUGGING LOG
        # Print old and new timing
        print("Old Time: ", dt)
        print("New Time: ", datetime_result)

        return unix_timestamp
