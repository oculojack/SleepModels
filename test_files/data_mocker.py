import json

#Tuesday, January 31, 2023 8:00:00 AM GMT-05:00 == 1675170000
ten_hours = 10 * 60 * 60
twenty_four_hours = 24 * 60 * 60

endDate = 1675170000.0
sleeps = []
for _ in range(60):
    startDate = endDate - ten_hours
    sleep = {"value": 0, "endDate": endDate, "startDate": startDate, "source": "Apple Watch", "timezone": -5}
    sleeps += [sleep]
    endDate = endDate + twenty_four_hours

final_dict = {"SleepSample": sleeps}

with open("sleep_sample_mocked.json", "w") as outfile:
    json.dump(final_dict, outfile)