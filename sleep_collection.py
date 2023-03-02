"""
Functions used for collecting sleep. Handles steps, 
    healthkit sleep (sleep sample), and acceleration (accelerometer sample)
 
    functions that return sleep return a dictionary 
        {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": datetime}} 
dates in the number of seconds since 00:00:00 UTC 1 January 1970
timezone: offset from UTC


"""

import pandas as pd
import numpy as np
from scipy.stats import norm

import json

from datetime import datetime, timedelta, date, time, timezone


CUTOFF_VALUE = 900 * 60 #if sleep minutes is over this value, data collection went wrong.


"""
Find all the sleep times within the recieved data
Returns a dictionary of sleep of the form
    {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": datetime}} 
        "source" can be a name of a source from healthkit or "acceleration"
"""
def getSleep(sleep_sample_data, acceleration_data):

    #need to extract timezone for later
    hkSleep, timezone = getSleepFromSleepSample(sleep_sample_data) if not sleep_sample_data == None else None, None
    accelerationSleep = getSleepFromAccelerationSample(acceleration_data) if not acceleration_data == None else None

    if hkSleep == None or len(hkSleep) == 0: 
        first_hk_occurance = None
    else: first_hk_occurance = sorted(hkSleep.items())[0][0]

    if accelerationSleep == None or len(accelerationSleep) == 0:
        first_accel_occurance = None
    else: first_accel_occurance = sorted(accelerationSleep.items())[0][0]

    if first_accel_occurance == None and first_hk_occurance == None:
        # no sleep recorded
        return None, None

    elif first_accel_occurance == None:
        begin_date = first_hk_occurance
    elif first_hk_occurance == None:
        begin_date = first_accel_occurance
    else:
        begin_date = min(first_hk_occurance, first_accel_occurance)
    
    sleep_dictionary = dict()
    if accelerationSleep == None:
        all_days = set(list(hkSleep.keys()))
    elif hkSleep == None:
        all_days = set(list(accelerationSleep.keys()))
    else:
        all_days = set(list(hkSleep.keys())) | set(list(accelerationSleep.keys()))

    for day in all_days:
        if day in hkSleep and hkSleep[day]['source'] != "Clock":
            sleep_dictionary[day] = hkSleep[day]
        elif day in accelerationSleep:
            sleep_dictionary[day] = accelerationSleep[day]
        else:
            # when there's no data for that day, repeat the sleep from yesterday
            # POSSIBLE CHANGE: could do some gaussian method of substitution
            yesterday = begin_date + timedelta(days=day-1)
            sleep_dictionary[day] = sleep_dictionary[yesterday]
    
    return sleep_dictionary, timezone

"""
------------------------------------Sleep Sample------------------------------------

https://developer.apple.com/documentation/healthkit/hkcategoryvaluesleepanalysis/inbed 
[
    {
        "startDate": 1659571317.2464128,
        "endDate": 1659575317.2464128,
        "timezone": -7,
        "value": 1,
        "source": "WHOOP"
    }
]
value: 
    0: inBed
    1: asleepUnspecified
    2: awake
    3: asleepCore
    4: asleepDeep
    5: asleepREM
"""

"""
Find all the sleep times within the recieved data
Returns a dictionary of sleep of the form
    {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
"""
def getSleepFromSleepSample(data):

    sleep_dict = {}

    for sample in data:
        timezone = sample["timezone"]
        if sample["value"] == 0:

            wakeup_time, wakeup_day, fallasleep_time = getHKTimes(sample)

            duration = (wakeup_time - fallasleep_time).seconds
            # Sometimes there are multiple inBed states in one sleep event
            if wakeup_day not in sleep_dict:
                if duration > CUTOFF_VALUE: duration = CUTOFF_VALUE
                sleep_dict[wakeup_day] = {"duration": duration, "source": sample["source"], "sleep": fallasleep_time, "wake": wakeup_time}
            else:
                if sleep_dict[wakeup_day]["duration"] + duration < CUTOFF_VALUE - duration:
                    sleep_dict[wakeup_day]["duration"] = sleep_dict[wakeup_day]["duration"] + duration
            
        duration = 0
        
    return sleep_dict, timezone


def getHKTimes(sample):
    tz = sample["timezone"]
    tz = timezone(timedelta(hours=tz))

    wakeup_timestamp = sample["endDate"]
    wakeup_time = datetime.fromtimestamp(wakeup_timestamp, tz)
    wakeup_day = wakeup_time.date()

    fallasleep_timestamp = sample["startDate"]
    fallasleep_time = datetime.fromtimestamp(fallasleep_timestamp, tz)

    return wakeup_time, wakeup_day, fallasleep_time

"""
------------------------------------Accelerometer Sample ------------------------------------
https://developer.apple.com/documentation/coremotion/cmsensorrecorder/1615987-recordaccelerometer
[
    {
        "timestamp": 1659571317.2464128,
        "timezone": -7,
        "x": 1,
        "y": 1,
        "z": 1
    }
]
"""
"""
Find all the sleep times within the recieved data
Returns a dictionary of sleep of the form
        {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
"""
def getSleepFromAccelerationSample(data):
  
    sleep_duration = 0
    sleeping = False

    fall_asleep_time = data[0]["timestamp"]
    tz = data[0]["timezone"]
    tz = timezone(timedelta(hours=tz))

    pastx, pasty, pastz = 0, 0, 0

    sleep_dict = {}
    
    for sample in data:

        timestamp = datetime.fromtimestamp(sample["timestamp"], tz)
        x = sample["x"]
        y = sample["y"]
        z = sample["z"]

        xmove = abs(pastx - x) > 0.5
        ymove = abs(pasty - y) > 0.5
        zmove = abs(pastz - z) > 0.5 

        #hasn't moved since last timestamp
        if not (xmove or ymove or zmove):
            if timestamp - fall_asleep_time > timedelta(hours=4):
                sleeping = True
        elif sleeping: #has moved and sleeping
            sleep_duration = timestamp - fall_asleep_time
            day = timestamp.date()
            wakeup_time = timestamp
            if day in sleep_dict:
                sleep_dict[day]["duration"] += sleep_duration
            else:
                sleep_dict[day] = {"duration": sleep_duration, "source": "acceleration", "sleep": fall_asleep_time, "wake": wakeup_time}
            sleeping = False
        else:
            pastx, pasty, pastz = x, y, z
            fall_asleep_time = timestamp

    return sleep_dict


"""
------------------------------------Steps------------------------------------

{
    "steps": [
        {
            "startDate": 1659571317.2464128,
            "endDate": 1659575317.2464128,
            "timezone": -7,
            "value": 1,
            "source": "WHOOP"
        }
    ]
}
Returns a dictionary of sleep of the form
    {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
"""

def getSleepFromSteps(data, disturbance_steps = 8,first_sleep_duration=3):
    '''
    Find sleep durations based on steps from past year
    disturbance steps: how many steps before it is a wakeup versus a disturbance
    first_sleep_duration: how many hours is the first sleep_duration chunk

    Return: past year of sleep {date: {duration:, source:}
    '''

    sleep_dict = {}

    # used to keep adding durations on to first large sleep event incase there are micro wakeups
    sleeping = False
    last_steps_time = datetime(1, 1, 1)

    steps_time, steps_day = getStepsTimes(data["steps"][0])
    last_steps_time = steps_time

    for record in data["steps"][1:]:

        steps_time, steps_day = getStepsTimes(record)
        sleep_duration = (steps_time - last_steps_time).seconds

        if sleep_duration > timedelta(hours = first_sleep_duration):
            sleeping = True
            if sleep_duration > CUTOFF_VALUE: sleep_duration = CUTOFF_VALUE
            sleep_dict[steps_day] = {"duration": sleep_duration, "source": "Steps", "sleep": None, "wake": None}
        elif sleeping:
            if sleep_dict[steps_day]["duration"] + sleep_duration < CUTOFF_VALUE - sleep_duration:
                sleep_dict[steps_day]['duration'] += sleep_duration

        #if there are many steps, assume user is awake
        if int(record.get("value")) > disturbance_steps:
            sleeping = False
        
        last_steps_time = steps_time

    return sleep_dict

def getStepsTimes(record):
    tz = record["timezone"]
    tz = timezone(timedelta(hours=tz))

    steps_timestamp = record["startDate"]
    steps_time = datetime.fromtimestamp(steps_timestamp, tz)
    steps_day = steps_time.date()  

    return steps_time, steps_day 


"""
Get the past year of sleep with a combination of hksleep and steps
Only used in inital OSD calculation

Returns a dictionary of sleep of the form
    {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
"""
def getPastYearsSleep(sleep_file, steps_file):

    hksleep = getSleepFromSleepSample(sleep_file)
    stepsleep = getSleepFromSteps(steps_file)

    # find when data collection begins
    last_year = date.today() - timedelta(days=365)
    first_hk_occurance = sorted(list(hksleep.items()))[0][0]
    first_stepsource_occurance = sorted(list(stepsleep.items()))[0][0]
    begin_date = min([last_year, first_hk_occurance, first_stepsource_occurance])
    
    print("Begin date: " + str(begin_date))

    sleep_dictionary = dict()

    for day in range(1, 365):
        today = begin_date + timedelta(days=day)
        if today in hksleep and hksleep[today]['source'] != "Clock":
                sleep_dictionary[today] = {"duration": hksleep[today]['duration'], "source": hksleep[today]['source'], "sleep": None, "wake": None}
        elif today in stepsleep:
            sleep_dictionary[today] = {"duration": stepsleep[today]['duration'], "source": stepsleep[today]['source'], "sleep": None, "wake": None}
        else:
            # when there's no data for that day, repeat the sleep from yesterday
            # POSSIBLE CHANGE: could do some gaussian method of substitution
            yesterday = begin_date + timedelta(days=day-1)
            sleep_dictionary[today] = sleep_dictionary[yesterday].copy()
    
    return sleep_dictionary

if __name__ == "__main__":
    getSleep("test_files/sleep_sample.json", "test_files/accelerometer_sample.json")