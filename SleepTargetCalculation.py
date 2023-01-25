from SleepTargetsModel import SleepTargetsModel
from SleepTargetsTraining import *
import json

class SleepTargetCalculation():

    def get(self, data):

        f = open(data)
        data = json.load(f)
        f.close()

        database = data["dataFromDatabase"]
        #inputs to model
        burn_prev = data["burnPrev"]
        burn_now = data["burnNow"]
        last_sleep = data["lastSleep"]
        weights = database["weights"]

        model = SleepTargetsModel()
        x = burn_now - burn_prev
        y = last_sleep

        if len(weights) == 0: #train with fake data
            x = 

        bt = model.predict(weights, burn_now) #tuple

        burn_targets = {"low": str(bt[0]), "med": str(bt[1]), "high": str(bt[2])}

        return burn_targets