from re import L
from sklearn.linear_model import SGDRegressor
import numpy as np

class SleepTargetsModel():
    MORING_BURN_DIF = 20
    LOW = 10 + MORING_BURN_DIF
    MED = 50 + MORING_BURN_DIF
    HIGH = 100 + MORING_BURN_DIF

    def __init__(self):
        self.model = SGDRegressor(warm_start = True)
    
    def fit(self, X, y):
        if isinstance(X, int):
            X = np.array([[X]])
        if isinstance(y, int):
            y = np.array([y])

        model = self.model
        model.fit(X, y)
        return model.score(X, y)
    
    def predict(self, burn):
        model = self.model
        low, med, high = burn-self.LOW, burn-self.MED, burn-self.HIGH
        low = model.predict(low) - self.MORING_BURN_DIF
        med = model.predict(med) - self.MORING_BURN_DIF
        high = model.predict(high) - self.MORING_BURN_DIF
        return (low, med, high)
    
    def predict_burn_change(self, sleep_duration):
        #use parameters of model to back-calculate burn change
        coef = self.model.coef_.reshape(-1)[0]
        intercept = self.model.coef_.reshape(-1)[0]
        change = (sleep_duration - intercept) / coef
        return change
    
    