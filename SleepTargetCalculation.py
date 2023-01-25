"""
Class used to receive sleep targets call, calculate sleep targets, and return them.
"""

from SleepTargetsModel import SleepTargetsModel
import json

class SleepTargetCalculation():

    MAX_SLEEP = 14 * 60 * 60

    def get(self, data):
        """
        Recieves a pieces of data from the backend and uses an instance of SleepTargetsModel
        to calculate sleep targets
        """
        f = open(data)
        data = json.load(f)
        f.close()

        #inputs to model
        if not data.get('burnPrev'):
            return None

        prev_burn = data["burnPrev"]
        burn = data["burn"]
        last_sleep = data["lastSleep"]

        model = SleepTargetsModel()

        if not data.get('weights'): #train with fake data if no data present
            coef, intercept = model.train(burn, prev_burn, last_sleep)
        else:
            weights = data["weights"]
            coef = weights["coef"]
            intercept = weights['intercept']

        low,med,high = model.predict(coef, intercept, burn)
        if high < 0: high = 0
        if low > self.MAX_SLEEP: low = self.MAX_SLEEP

        sleep_targets = {"low": low, "med": med, "high": high}

        return sleep_targets