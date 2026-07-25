import re
with open(r'C:\Users\ASUS\ecoloop\5ZoneAirCooled.idf', 'r') as f:
    c = f.read()
schedules = re.findall(r'Schedule:Compact,\s*([^,]+),', c)
for s in schedules:
    print(repr(s.strip()))