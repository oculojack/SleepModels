"""
Called when recieve a night of sleep. This will come as two json files, one for acceleration and one for healthkit.
"""

from torch import NoneType
from SleepTargetsModel import SleepTargetsModel
from sleep_collection import *
from datetime import datetime, timedelta, date, time, timezone

class SleepModel():
    FOCUS_TIMELINE_RANGE = (60, 100)
    REST_DURATION = 20 * 60
    SLEEP_RECOVERY_TIME = timedelta(seconds = 3600 * 1.5)
    
    def get(self, data):
        """
        Returns a dictionary with all the outputs of the sleep model
        Fills values that cannot be found with None
        """
        f = open(data)
        data = json.load(f)
        f.close()

        ios = data["dataFromIOS"]
        database = data["dataFromDatabase"]

        #inputs to model
        sleep_sample = ios["SleepSample"]
        accelerometer_sample = ios["AccelerometerSample"]
        weights = database["weights"]
        burn = database["burn"]

        sleep_dict, self.timezone = getSleep(sleep_sample, accelerometer_sample)
        sleepLastNight, sleepTimeline = self.get_last_night(sleep_dict)

        if sleepLastNight == None:
            # No data for sleep last night
            return None

        recoveryBurn, recoveryScore = self.get_recovery_burn(weights, sleepLastNight, burn)

        if not recoveryBurn == None:
            focusTimeline = self.get_focus_timeline(recoveryBurn, sleepTimeline)
        else: focusTimeline = None

        print(self.create_dict(sleepLastNight, sleepTimeline, recoveryBurn, recoveryScore, focusTimeline))

    def get_last_night(self, sleep_dict):
        """
        If there was recorded sleep last night, return the duration and timestamps
        Otherwise, return None
        sleep_dict: {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
        """
        if len(sleep_dict) == 0:
            return None, None
        sortedlist = sorted(sleep_dict.items())
        most_recent = sortedlist[-1]
        if not most_recent[0] == date.today():
            return None, None
        else:
            duration = most_recent[1]["duration"]
            sleepTimeline = {"start": most_recent[1]["sleep"], "end": most_recent[1]["wake"], "timezone": self.timezone}
            return duration, sleepTimeline
    
    def get_recovery_burn(self, weights, sleepLastNight, last_burn):
        """
        If there is a sleepTargetsModel for the user, return the recoveryBurn and recoveryScore
        Otherwise, return None
        filepath: filepath to user's model, should be UserID
        sleepLastNight: duration of sleep last night
        last_burn: the last burn score of the user
        """
        model = SleepTargetsModel()
        if len(weights) > 0:
            coef, intercept = weights["coef"], weights["intercept"]
            change = model.predict_burn_change(coef, intercept, sleepLastNight)
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
        if focus_duration > self.FOCUS_TIMELINE_RANGE[1]: focus_duration = self.FOCUS_TIMELINE_RANGE[1]
        if focus_duration < self.FOCUS_TIMELINE_RANGE[0]: focus_duration = self.FOCUS_TIMELINE_RANGE[0]

        sleep = {"start": sleepTimeline["start"].timestamp(), "end": sleepTimeline["end"].timestamp(), "level": 0, "timezone": self.timezone}
        sleep_recovery_end = sleepTimeline["end"] + self.SLEEP_RECOVERY_TIME
        sleep_recovery = {"start": sleepTimeline["end"].timestamp(), "end": sleep_recovery_end.timestamp(), "level": 1, "timezone": self.timezone}

        timeline = [sleep, sleep_recovery]
        start = sleep_recovery_end
        end = sleepTimeline["start"]
        level = 1
        while start.hour < 21:
            if level == 1:
                end = start + timedelta(seconds=focus_duration)
                level = 2
            else:
                end = start + timedelta(seconds=self.REST_DURATION)
                level = 1
            interval = {"start": start.timestamp(), "end": end.timestamp(), "level": level, "timezone": self.timezone}
            timeline.append(interval)
            start = end

        sleep = {"start": end.timestamp(), "end": (end + timedelta(seconds=3600 * 4)).timestamp(), "level": 0, "timezone": self.timezone}
        timeline.append(sleep)
        return timeline

    def create_dict(self, sleepLastNight=None, sleepTimeline=None, recoveryBurn=None, recoveryScore=None, focusTimeline=None):
        sleepTimeline['start'] = sleepTimeline['start'].timestamp()
        sleepTimeline['end'] = sleepTimeline['end'].timestamp()
        return {"sleepLastNight": sleepLastNight, "sleepTimeline": sleepTimeline, 
        "recoveryBurn": recoveryBurn, "recoveryScore": recoveryScore, "focusTimeline": focusTimeline}
    