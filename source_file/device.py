import math
import os
import requests
import typing
import cvzone
import numpy as np
from logger import Logger
from people import Person
from memory_profiler import profile

class Device:

    def __init__(self, name, interval):
        self.name = name
        self.current_directory = os.getcwd()
        self.recording = False
        self.Interval = interval
        self.Stop = False
        self.objects: list = []
        self.angle_memory: typing.Dict[str, list] = self.get_dict()
        self.is_flicker = 0

    def get_dict(self):
        dict = {}
        try:
            contents = requests.get("http://127.0.0.1:8000/partner/").json()
            if len(contents) > 0:
                for item in contents:
                    surveillance_name_from = "surveillance-" + str(item['from_person'])
                    surveillance_name_to = "surveillance-" + str(item['to_person'])
                    if surveillance_name_from == self.name:
                        dict[surveillance_name_to] = [item['angle_start'], item['angle_end']]
                return dict
            else:
                return None
        except requests.exceptions.HTTPError:
            raise Exception("HTTP Request Error. Angle Memory not initialised. Application will not run for device class")

    #@profile()
    def get_next_camera_id(self, magnitude):
        for x in self.angle_memory:
            if self.angle_memory[x][0] < math.floor(magnitude) < self.angle_memory[x][1]:
                print(self.angle_memory)
                print("Object within surveillance zone: " + x)
                return x
            else:
                print("Object out of surveillance zone", math.floor(magnitude))
                return None

    #@profile()
    def check_object_addition_or_updates(self, current_centroid_detected, previous_people_group, logger: Logger):
        # Loop through all current centroids detected
        if len(current_centroid_detected) > 0:

            for centroid in current_centroid_detected:

                # created boolean to check if object is new
                not_found = True

                # Check if centroid is already from the previous DataFrame
                for person_previous in previous_people_group:

                    # Check if Euclidean < 200
                    if (0 <= abs(math.dist(centroid[1], person_previous.centroid)) < 200) and (centroid[0] == person_previous.id):

                        # Calculate magnitude
                        print("Existing Object Position Moved: ", person_previous.id)
                        direction = self.calculate_magnitude(centroid[1], person_previous.centroid)

                        # Assign new magnitude to existing person
                        person_previous.magnitude = direction
                        print("Angle of movement:", direction)

                        # Write to log file
                        logger.write_report("text", "Existing Object Position Moved: " + str(person_previous.id) + ", Angle of movement: " + str(direction))

                        # Assign new centroid to existing centroid
                        person_previous.centroid = centroid[1]
                        not_found = False

                if not_found:
                    # Add new centroid to object list
                    print("New Object ID Found: ", centroid[0])
                    logger.write_report("text", "New Object ID Found: " + str(centroid[0]))
                    self.objects.append(Person(centroid[0], centroid[1]))

    #@profile()
    def check_out_of_frame(self, previous_frame, current_frame, object_id):

        print(previous_frame)

        for item in previous_frame:

            # created boolean to check if object is out of frame
            not_found = True

            for centroid in current_frame:
                # DEBUGGING LOG
                # print(centroid[1], item.centroid)

                # Check if Euclidean < 100
                if 0 <= abs(math.dist(centroid[1], item.centroid)) < 100:
                    print("Object found, not missing")
                    self.is_flicker = 0
                    not_found = False

            if not_found:

                print("User object not found, checking", item)

                # Check if existing items still exist
                if int(item.id[0]) == int(object_id):
                    print("Object ID found, verified!")
                    # DEBUGGING LOG
                    # Print last recorded magnitude
                    # print("Last marked magnitude: ", item.magnitude)
                    return item.magnitude
                    # Remove out of frame objects
                    self.objects.remove(item)
                else:
                    print("User object not found, but exist, checking flicker")
                    if self.is_flicker > 4:
                        # DEBUGGING LOG
                        # Print last recorded magnitude
                        # print("Last marked magnitude: ", item.magnitude)
                        print("Flicker check failed, Object officially out of frame")
                        return item.magnitude
                        # Remove out of frame objects
                        self.objects.remove(item)
                    else:
                        print("Object potential flicker: " + str(self.is_flicker))
                        self.is_flicker += 1

    #@profile()
    def draw_bounding_boxes(self, id, box, class_names, img):

        # Bounding Box (Get axis of x1, x2, width, height)
        x1, y1, x2, y2 = box.xyxy[0]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        w, h = x2 - x1, y2 - y1
        cvzone.cornerRect(img, (x1, y1, w, h))

        # Confidence
        conf = math.ceil((box.conf[0] * 100)) / 100

        # Class Name
        cls = int(box.cls[0])

        cvzone.putTextRect(img, "name: " + class_names[cls], (max(0, x1), max(35, y1)), scale=2, thickness=1)
        cvzone.putTextRect(img, "conf: " + str(conf), (max(0, x1), max(35, y1 - 35)), scale=2, thickness=1)
        cvzone.putTextRect(img, "id: " + str(id), (max(0, x1), max(35, y1 - 70)), scale=2, thickness=1)

        # Get centroid of each box
        x, y = self.get_centroid(x1, y1, w, h)
        current_centroid = [x, y]

        # Return centroid and id
        return current_centroid, id

    @staticmethod
    def get_centroid(x, y, w, h):
        return [x + (w / 2), y + (h / 2)]

    @staticmethod
    def calculate_magnitude(current_centroid, previous_centroid):
        w, h = [current_centroid[0] - previous_centroid[0], current_centroid[1] - previous_centroid[1]]
        angle_of_facing = (np.rad2deg(np.arctan2(h, w)) + 360) % 360
        return angle_of_facing
