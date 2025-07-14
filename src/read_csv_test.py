import pandas as pd

'''
data = {
    "Name": ["Tony", "Stark"],
    "Date": ["04-07-2025", "03-05-2025"],
    "Time": ["9:00", "8:30"]
}

df = pd.DataFrame(data)
df.to_csv("D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/data/attendance_data.csv", index=False)
'''

read = pd.read_csv("D:/Courses/Intel_AI_Course/Project_1/attendance_fillup_agent/data/attendance_data.csv")
print(read)