"""
Functions used for collecting sleep. Handles steps, healthkit sleep, and acceleration

    functions that return sleep return a dictionary 
        {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
dates in the number of seconds since 00:00:00 UTC 1 January 1970
timezone: offset from UTC


"""

import pandas as pd
import numpy as np
from scipy.stats import norm

import json

from datetime import datetime, timedelta, date, time, timezone


CUTOFF_VALUE = 900 #if sleep minutes is over this value, data collection went wrong.


"""
Find all the sleep times within the recieved data
Returns a dictionary of sleep of the form
    {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
        "source" can be a name of a source from healthkit or "acceleration"
"""
def getSleep(hksleep_file, acceleration_file):

    hkSleep = getSleepFromHealthKit(hksleep_file)
    accelerationSleep = getSleepFromAcceleration(acceleration_file)

    first_hk_occurance = sorted(hkSleep.items())[0][0]
    first_accel_occurance = sorted(accelerationSleep.items())[0][0]
    begin_date = min(first_hk_occurance, first_accel_occurance)
    
    print("Begin date: " + str(begin_date))

    sleep_dictionary = dict()
    all_days = set(list(hkSleep.keys())) | set(list(accelerationSleep.keys()))

    for day in all_days:
        if day in hkSleep and hkSleep[day]['source'] != "Clock":
                sleep_dictionary[day] = {"duration": hkSleep[day]['duration'], "source": hkSleep[day]['source']}
        elif day in accelerationSleep:
            sleep_dictionary[day] = {"duration": accelerationSleep[day]['duration'], "source": accelerationSleep[day]['source']}
        else:
            # when there's no data for that day, repeat the sleep from yesterday
            # POSSIBLE CHANGE: could do some gaussian method of substitution
            yesterday = begin_date + timedelta(days=day-1)
            sleep_dictionary[day] = {"duration": sleep_dictionary[yesterday]['duration'], "source": sleep_dictionary[yesterday]['source']}
    
    return sleep_dictionary

"""
------------------------------------HealthKit Sleep------------------------------------

https://developer.apple.com/documentation/healthkit/hkcategoryvaluesleepanalysis/inbed 
{
    "hksleep": [
        {
            "startDate": 1659571317.2464128,
            "endDate": 1659575317.2464128,
            "timezone": -7,
            "value": 1,
            "source": "WHOOP"
        }
    ]
}
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
def getSleepFromHealthKit(filename = "mock_hksleep.json"):
    
    f = open(filename)
    data = json.load(f)

    sleep_dict = {}

    for record in data["hksleep"]:
        if record["value"] == 0:

            wakeup_time, wakeup_day, fallasleep_time = getHKTimes(record)

            duration = (wakeup_time - fallasleep_time).seconds / 60
            # Sometimes there are multiple inBed states in one sleep event
            if wakeup_day not in sleep_dict:
                sleep_dict[wakeup_day] = {"duration": duration,\
                    "source": record.get("sourceName"), "sleep": fallasleep_time, "wake": wakeup_time}
            else:
                sleep_dict[wakeup_day]["duration"] = sleep_dict[wakeup_day]["duration"] + duration

    sleep_dict = map(lambda x: x["duration"] if x['duration'] < CUTOFF_VALUE else CUTOFF_VALUE, sleep_dict)

    return sleep_dict


def getHKTimes(record):
    tz = record["timezone"]
    tz = timezone(timedelta(hours=int(tz[:3])))

    wakeup_timestamp = record["startDate"]
    wakeup_time = datetime.fromtimestamp(wakeup_timestamp, tz)
    wakeup_day = wakeup_time.date()

    fallasleep_timestamp = record["endDate"]
    fallasleep_time = datetime.fromtimestamp(fallasleep_timestamp, tz)

    return wakeup_time, wakeup_day, fallasleep_time

"""
------------------------------------Acceleration------------------------------------
https://developer.apple.com/documentation/coremotion/cmsensorrecorder/1615987-recordaccelerometer

Records at a rate of 50 hz.
{
    "acceleration": [
        {
            "timestamp": 1659571317.2464128,
            "timezone": -7,
            "x": 1,
            "y": 1,
            "z": 1
        }
    ]
}
"""
"""
Find all the sleep times within the recieved data
Returns a dictionary of sleep of the form
        {day (datetime day): {"duration": int, "source": String, "sleep": datetime, "wake": dateime}} 
"""
def getSleepFromAcceleration(filename):
  
    f = open(filename)
    data = json.load(f)
    
    sleep_duration = 0
    sleeping = False

    fall_asleep_time = data['acceleration'][0]["timestamp"]
    tz = data['acceleration'][0]["timezone"]
    tz = timezone(timedelta(hours=tz))

    pastx, pasty, pastz = 0

    sleep_dict = dict()
    
    for activity in data['acceleration']:

        timestamp = datetime.fromtimestamp(activity["timestamp"], tz)
        x = activity["x"]
        y = activity["y"]
        z = activity["z"]

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

    f.close()

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

def getSleepFromSteps(filename, disturbance_steps = 8,first_sleep_duration=3):
    '''
    Find sleep durations based on steps from past year
    disturbance steps: how many steps before it is a wakeup versus a disturbance
    first_sleep_duration: how many hours is the first sleep_duration chunk

    Return: past year of sleep {date: {duration:, source:}
    '''

    f = open(filename)
    data = json.load(f)

    sleep_dict = {}

    # used to keep adding durations on to first large sleep event incase there are micro wakeups
    sleeping = False
    last_steps_time = datetime(1, 1, 1)

    steps_time, steps_day = getStepsTimes(data["steps"][0])
    last_steps_time = steps_time

    for record in data["steps"][1:]:

        steps_time, steps_day = getStepsTimes(record)
        sleep_duration = steps_time - last_steps_time

        if sleep_duration > timedelta(hours = first_sleep_duration):
            sleeping = True
            
            sleep_dict[steps_day] = {"duration": (sleep_duration.seconds / 60), "source": "Steps", "sleep": None, "wake": None}
            
        elif sleeping:
            sleep_dict[steps_day]['duration'] += (sleep_duration.seconds / 60)

        #if there are many steps, assume user is awake
        if int(record.get("value")) > disturbance_steps:
            sleeping = False
        
        last_steps_time = steps_time

    sleep_dict = map(lambda x: x["duration"] if x['duration'] < CUTOFF_VALUE else CUTOFF_VALUE, sleep_dict)

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
def getPastYearsSleep(hksleep_file, steps_file):

    hksleep = getSleepFromHealthKit(hksleep_file)
    stepsleep = getSleepFromSteps(steps_file)

    # find when data collection begins
    last_year = date.today() - timedelta(days=365)
    first_hk_occurance = sorted(hksleep.items())[0][0]
    first_stepsource_occurance = sorted(stepsleep.items())[0][0]
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