from datetime import datetime

# data = 'Thu Dec  9 14:37:58 EET 2021'
data = 'Thu Dec  9 14:37:58 EET'
# ts = datetime.strptime(data, '%a %b %d %H:%M:%S %Z %Y')
ts = datetime.strptime(data, '%a %b %d %H:%M:%S %Z')
print(ts)
