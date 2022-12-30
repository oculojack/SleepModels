import pickle
from sleep_collection import *
import os.path
from SleepTargetsModel import SleepTargetsModel
import numpy as np

class SleepTargetCalculation():

    def get(self):

        #inputs to model
        burn_prev, burn_now = self.fetchBurn()
        last_sleep = self.fetchSleep()
        filepath = self.fetchFilepath() #should be the user ID

        if os.path.exists(filepath):
            model = pickle.load(open(filepath, 'rb'))
            X = np.array([[burn_now - burn_prev]])
            y = np.array([last_sleep])
        else:
            model = SleepTargetsModel()
            #initialize intercept as (0, 7.5)
            X = np.array([[burn_now - burn_prev], [0]])
            y = np.array([last_sleep, 7.5])

        model.fit(X, y)
        pickle.dump(model, open(filepath, 'wb'))

        bt = model.predict(burn_now) #tuple
        burn_targets = {"low": str(bt[0]), "med": str(bt[1]), "high": str(bt[2])}
        return burn_targets
    
    
    """
    Returns a file path that should be the id of the user
    """
    def fetchFilepath(self):
        return "sleep_targets_model.sav"

    """
    Fetch burn from startDate to endDate, from data lake
    """
    def fetchBurn(self, startDate, endDate):
        return {}

    """
    Fetch sleep from last night
    """
    def fetchSleep(self):
        return {}
