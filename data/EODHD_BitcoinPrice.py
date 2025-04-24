# import requests
# import json
#
# API_KEY = 'INSERT_KEY_KOSTAS'
# SYMBOL = 'btc-usd.cc'
# FROM_DATE = '2021-01-01'
# TO_DATE = '2024-12-31'
#
# url = f'https://eodhd.com/api/eod/{SYMBOL}'
# params = {
#     'api_token': API_KEY,
#     'from': FROM_DATE,
#     'to': TO_DATE,
#     'period': 'd',  # daily data
#     'fmt': 'csv'
# }
#
# response = requests.get(url, params=params)
#
# if response.status_code == 200:
#     data = response.csv()
#     with open('bitcoin_2021_2024.json', 'w') as f:
#         json.dump(data, f, indent=2)
#     print("Data saved to bitcoin_2021_2024.csv")
# else:
#     print(f"Failed to fetch data: {response.status_code}, {response.text}")

import requests
import csv

API_KEY = 'INSERT_KEY_KOSTAS'
SYMBOL = 'btc-usd.cc'
FROM_DATE = '2021-01-01'
TO_DATE = '2024-12-31'

url = f'https://eodhd.com/api/eod/{SYMBOL}'
params = {
    'api_token': API_KEY,
    'from': FROM_DATE,
    'to': TO_DATE,
    'period': 'd',
    'fmt': 'json'
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()

    # Save to CSV
    with open('bitcoin_2021_2024.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print("Data saved to bitcoin_2021_2024.csv")
else:
    print(f"Failed to fetch data: {response.status_code}, {response.text}")

