class Person:

    def __init__(self, id, centroid):
        self.id = id
        self.centroid = centroid
        self.counted = False
        self.invisible = False
        self.magnitude = 0

    def get_centroid(self):
        return self.centroid

    def get_magnitude(self):
        return self.magnitude
