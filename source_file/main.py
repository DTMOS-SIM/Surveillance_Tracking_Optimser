import cProfile
import os
import datetime
import pstats
from system import System
from logger import Logger
from memory_profiler import profile
from test import AccuracyCalculator


@profile()
def main(timestamp, surveillance, counter, id=None):
    # Initialise Singleton Logger
    log = Logger()
    # Initialise Singleton Accuracy Calculator
    accuracy_calculator = AccuracyCalculator()

    # Get the file location
    dir_path = os.path.dirname(os.path.realpath(__file__))

    # Declare global variable for surveillance folder and initial selected footage
    surveillance_folder = dir_path + "/demo_vids/" + surveillance
    files = [f for f in os.listdir(surveillance_folder) if os.path.isfile(os.path.join(surveillance_folder, f))]
    selected_footage = surveillance_folder + "/" + str(int(timestamp)) + ".mp4"
    cutoff_frame = None

    # Check if file exist
    if not os.path.exists(selected_footage):

        # Sort the files in order
        new_list = [file.split('.')[0] for file in files]
        new_list.sort(reverse=True)

        # Iterate through list to get correct file time series
        for file in new_list:
            # Get the latest recorded footage based on time frame sequencing
            if int(file) < int(timestamp):
                # Re-assigned footage file path to user
                selected_footage = surveillance_folder + "/" + str(file) + ".mp4"
                # Set cut of frame
                cutoff_frame = (datetime.datetime.fromtimestamp(int(timestamp)) - datetime.datetime.fromtimestamp(
                    int(file))).total_seconds()
                break

    # Initialise System
    print("Scanning Footage: ", )

    # Initialise System Class
    operating_system = System(selected_footage, timestamp, log, surveillance)

    # Check if next call for main have id as parameter value
    if id is not None:
        # Log Surveillance Name
        log.write_report('chapter_title', str(surveillance) + str(timestamp))
        # Create new result by calling run video scan again function
        results = operating_system.run_video_scan(counter, object_id=id)
    else:
        # Check if cutoff frame is used for video processing instead of counter value
        if cutoff_frame is not None:
            results = operating_system.run_video_scan(None, unprocessed_second=cutoff_frame)
        else:
            results = operating_system.run_video_scan(counter)

    # Check if returning result from run_video_scan is the final scenario before disappearing
    if results is not None:
        log.write_report("chapter_title", str(results['surveillance']))
        operating_system.disposed_data()
        operating_system.empty_gpu_cache()
        main(results['timestamp'], results['surveillance'], results['frame'])
    else:
        # Create Accuracy Log Header
        log.write_report(
            "chapter_title",
            "Total Tracking and Detection Accuracy: " + str(accuracy_calculator.calculate_acc())
        )
        # Write Accuracy Output
        log.write_report(
            "text",
            "Detected Frames: " +
            str(accuracy_calculator.get_detected_frames()) +
            "\n Total Frames: " +
            str(accuracy_calculator.get_total_frames()) +
            "\n Accuracy Percentage: " +
            str(accuracy_calculator.calculate_acc())
        )
        # End Report Design
        log.write_report("chapter_title", "Generation complete")
        # Generate Report
        log.generate_report()

    print("Generation Complete: ", results)


if __name__ == "__main__":
    main("1693117579", "surveillance-1", 100)
