"""
Called when recieve a night of sleep. This will come as two json files, one for acceleration and one for healthkit.
"""

from SleepTargetsModel import SleepTargetsModel
from sleep_collection import *
from datetime import datetime, timedelta, date, time, timezone
import os.path
import pickle

class SleepModel():
    FOCUS_TIMELINE_RANGE = (60, 100)
    REST_DURATION = 20 * 60
    SLEEP_RECOVERY_TIME = timedelta(seconds = 3600 * 1.5)
    
    def get(self):
        """
        Returns a dictionary with all the outputs of the sleep model
        Fills values that cannot be found with None
        """
        #inputs to model
        sleep_sample = self.fetch_sleep_sample()
        acceleration_sample = self.fetch_acceleration_sample()
        filepath = self.fetch_filepath() #should be the user ID
        last_burn = self.fetch_last_burn() #should be the user ID

        # sleep_dict: {day (datetime day): {"duration": int, "source": String}} 
        sleep_dict = getSleep(sleep_sample, acceleration_sample)
        sleepLastNight, sleepTimeline = self.get_last_night(sleep_dict)
        if sleepLastNight == None:
            # No data for sleep last night
            return None
        recoveryBurn, recoveryScore = self.get_recovery_burn(filepath, sleepLastNight, last_burn)
        if not recoveryBurn == None:
            focusTimeline = self.get_focus_timeline(recoveryBurn, sleepTimeline)
        else: focusTimeline = None

        return {"sleepLastNight": str(sleepLastNight), "sleepTimeline": str(sleepTimeline), "recoveryBurn": str(recoveryBurn),\
            "recoveryScore": str(recoveryScore), "focusTimeline": str(focusTimeline)}

    def get_last_night(self, sleep_dict):
        """
        If there was recorded sleep last night, return the duration and timestamps
        Otherwise, return None
        sleep_dict: {day (datetime day): {"duration": int, "source": String}} 
        """
        most_recent =  sorted(sleep_dict.items())[0]
        if not most_recent[0] == date.today():
            return None, None
        else:
            duration = most_recent[1]["duration"]
            sleepTimeline = {"start": most_recent[1]["sleep"], "end": most_recent[1]["wake"]}
            return duration, sleepTimeline
    
    def get_recovery_burn(self, filepath, sleepLastNight, last_burn):
        """
        If there is a sleepTargetsModel for the user, return the recoveryBurn and recoveryScore
        Otherwise, return None
        filepath: filepath to user's model, should be UserID
        sleepLastNight: duration of sleep last night
        last_burn: the last burn score of the user
        """
        if os.path.exists(filepath):
            model = pickle.load(open(filepath, 'rb'))
            change = model.predict_burn_change(sleepLastNight)
            recoveryBurn = last_burn + change
            return recoveryBurn, recoveryBurn - last_burn
        else:
            #recovery burn not available
            return None, None
    
    def get_focus_timeline(self, recovery_burn, sleepTimeline):
        """
        Return the focus timeline
        recoveryBurn: burn for this morning
        sleepTimeline: timestamps of sleep last night
        """

        fatigue_effect = (recovery_burn/100) * (self.FOCUS_TIMELINE_RANGE[1] - self.FOCUS_TIMELINE_RANGE[0])
        focus_duration = (self.FOCUS_TIMELINE_RANGE[1] - fatigue_effect) * 60

        sleep = {"start": sleepTimeline["start"], "end": sleepTimeline["end"], "level": 0}
        sleep_recovery_end = sleepTimeline["end"] + self.SLEEP_RECOVERY_TIME
        sleep_recovery = {"start": sleepTimeline["end"], "end": sleep_recovery_end, "level": 1}

        timeline = [sleep, sleep_recovery]
        start = sleep_recovery_end
        end = sleepTimeline["start"]
        level = 1
        while start < time(21):
            if level == 1:
                end = start + timedelta(seconds=focus_duration)
                level = 2
            else:
                end = start + timedelta(seconds=self.REST_DURATION)
                level = 1
            interval = {"start": start, "end": end, "level": level}
            timeline.append(interval)
            start = end

        sleep = {"start": end, "end": end + timedelta(3600 * 4), "level": 0}
        timeline.append(sleep)
        return timeline
            

    def fetch_sleep_sample(self):
        return None
    
    def fetch_acceleration_sample(self):
        return None
    
    def fetch_filepath(self):
        return None
    
    def fetch_last_burn():
        return None