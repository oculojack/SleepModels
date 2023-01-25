from SleepTargetsModel import SleepTargetsModel
import json

class SleepTargetCalculation():

    def get(self, data):

        f = open(data)
        data = json.load(f)
        f.close()

        #inputs to model
        if not data.get('burnPrev'):
            return None

        prev_burn = data["burnPrev"]
        last_burn = data["burnNow"]
        last_sleep = data["lastSleep"]

        model = SleepTargetsModel()

        if not data.get('weights'): #train with fake data if no data present
            coef, intercept = model.train(last_burn, prev_burn, last_sleep)
        else:
            weights = data["weights"]
            coef = weights["coef"]
            intercept = weights['intercept']

        bt = model.predict(coef, intercept, last_burn)

        burn_targets = {"low": str(bt[0]), "med": str(bt[1]), "high": str(bt[2])}

        print(burn_targets)
        return burn_targets

if __name__ == "__main__":
    blah = SleepTargetCalculation()
    blah.get("test_files/sleep_target_data.json")