class AccuracyCalculator(object):

    """
    SINGLETON CLASS CONFIGURATION
    Accuracy Calculator Class calls on top of Main Class which acts as a singleton class to allow only one instance to calculate the entire footage frame values
    """
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(AccuracyCalculator, cls).__new__(cls)
            cls.detected_frames = 0
            cls.total_frames = 0
        return cls.instance

    def get_detected_frames(self):
        return self.detected_frames

    def set_detected_frames(self):
        self.detected_frames += 1

    def get_total_frames(self):
        return self.total_frames

    def set_total_frames(self):
        self.total_frames += 1

    def calculate_acc(self):
        return (self.detected_frames/self.total_frames) * 100

