from re import L
from sklearn.linear_model import LinearRegression
import numpy as np

class SleepTargetsModel():
    MORING_BURN_DIF = 20
    LOW = 10 + MORING_BURN_DIF
    MED = 50 + MORING_BURN_DIF
    HIGH = 100 + MORING_BURN_DIF

    def __init__(self):
        self.model = LinearRegression()
    
    def fit(self, X, y):
        model = self.model
        model.fit(X, y)
        return model
    
    def predict(self, coef, intercept, burn):
        if coef.isinstance
        low, med, high = self.LOW-burn, self.MED-burn, self.HIGH-burn
        low = low*coef + intercept
        med = med*coef + intercept
        high = high*coef + intercept
        return (low, med, high)
    
    def train(self, last_burn, burn_prev, last_sleep):
        #initialize intercept as (0, 7.5)
        X = np.array([[last_burn - burn_prev], [0]])
        y = np.array([last_sleep, 7.5*60*60])

        self.model.fit(X, y)
        return (self.model.coef_, self.model.intercept_)
    
    def predict_burn_change(self, coef, intercept, sleep_duration):
        #use parameters of model to back-calculate burn change
        change = (sleep_duration - intercept) / coef
        return change + self.MORNING_BURN_DIF
    
    