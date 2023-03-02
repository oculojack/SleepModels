"""
Called when recieve a night of sleep. This will come as two json files, one for acceleration and one for healthkit.
"""

from SleepTargetsModel import SleepTargetsModel
from sleep_collection import *
from datetime import datetime, timedelta, date, time, timezone

class SleepModel():
    FOCUS_TIMELINE_RANGE = (60, 100)
    REST_DURATION = 20 * 60
    SLEEP_RECOVERY_TIME = timedelta(seconds = 3600 * 1.5)
    SLEEP_BASELINE = timedelta(seconds = 3600 * 8)
    
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
        sleep_sample = ios["SleepSample"] if "SleepSample" in ios else None
        accelerometer_sample = ios["AccelerometerSample"] if "AccelerometerSample" in ios else None
        weights = database["weights"] if "weights" in ios else None
        burn = database["burn"] if "burn" in ios else None

        sleep_dict, self.timezone = getSleep(sleep_sample, accelerometer_sample)

        if sleep_dict == None:
            # No data for sleep last night
            print("No sleep recorded")
            return None

        sleepLastNight, sleepTimeline = self.get_last_night(sleep_dict)

        if sleepLastNight == None:
            # No data for sleep last night
            print("No sleep recorded")
            return None

        focusTimeline = self.get_focus_timeline(sleepLastNight, sleepTimeline)

        return self.create_dict(sleepLastNight, sleepTimeline, None, focusTimeline)

    def get_last_night(self, sleep_dict):
        """
        If there was recorded sleep last night, return the duration and timestamps
        Otherwise, return None
        sleep_dict: {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
        """
        if len(sleep_dict) == 0:
            return None, None
        for day,dict in sleep_dict.items():
            if day == date.today():
                duration = dict["duration"]
                sleepTimeline = {"start": dict["sleep"], "end": dict["wake"], "timezone": self.timezone}
                return duration, sleepTimeline
        return None, None
    
    def get_recovery_burn(self, weights, sleepLastNight, last_burn):
        """
        If there is a sleepTargetsModel for the user, return the recoveryBurn 
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
            return recoveryBurn
        else:
            #recovery burn not available
            return None
    
    def get_focus_timeline(self, sleepDuration, sleepTimeline):
        """
        Return the focus timeline
        recoveryBurn: burn for this morning
        sleepTimeline: timestamps of sleep last night
        """

        fatigue_effect =  (sleepDuration / self.SLEEP_BASELINE.seconds) * (self.FOCUS_TIMELINE_RANGE[1] - self.FOCUS_TIMELINE_RANGE[0])
        focus_duration = (self.FOCUS_TIMELINE_RANGE[1] - fatigue_effect) * 60
        if focus_duration > self.FOCUS_TIMELINE_RANGE[1]: focus_duration = self.FOCUS_TIMELINE_RANGE[1]
        if focus_duration < self.FOCUS_TIMELINE_RANGE[0]: focus_duration = self.FOCUS_TIMELINE_RANGE[0]

        sleep = {"start": int(sleepTimeline["start"].timestamp()), "end": int(sleepTimeline["end"].timestamp()), "level": 0, "timezone": self.timezone}
        sleep_recovery_end = sleepTimeline["end"] + self.SLEEP_RECOVERY_TIME
        sleep_recovery = {"start": int(sleepTimeline["end"].timestamp()), "end": int(sleep_recovery_end.timestamp()), "level": 1, "timezone": self.timezone}

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
            interval = {"start": int(start.timestamp()), "end": int(end.timestamp()), "level": level, "timezone": self.timezone}
            timeline.append(interval)
            start = end

        sleep = {"start": int(end.timestamp()), "end": int((end + timedelta(seconds=3600 * 4)).timestamp()), "level": 0, "timezone": self.timezone}
        timeline.append(sleep)
        return timeline

    def create_dict(self, sleepLastNight=None, sleepTimeline=None, recoveryBurn=None, focusTimeline=None):
        sleepTimeline['start'] = int(sleepTimeline['start'].timestamp())
        sleepTimeline['end'] = int(sleepTimeline['end'].timestamp())
        return {"sleepLastNight": sleepLastNight, "sleepTimeline": sleepTimeline, 
        "recoveryBurn": recoveryBurn,  "focusTimeline": focusTimeline}
    
# if __name__ == "__main__":
#     model = SleepModel()
#     print(model.get("test_files/payload_sparse.json"))