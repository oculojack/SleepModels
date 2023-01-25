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
    
    def predict(self, weights, burn):
        coef = weights["coef"]
        intercept = weights['intercept']
        low, med, high = burn-self.LOW, burn-self.MED, burn-self.HIGH
        low = low*coef + intercept - self.MORING_BURN_DIF
        med = med*coef + intercept - self.MORING_BURN_DIF
        high = high*coef + intercept - self.MORING_BURN_DIF
        return (low, med, high)
    
    def predict_burn_change(self, sleep_duration):
        #use parameters of model to back-calculate burn change
        coef = self.model.coef_.reshape(-1)[0]
        intercept = self.model.coef_.reshape(-1)[0]
        change = (sleep_duration - intercept) / coef
        return change
    
    