# keywords = [
#     'BTC', 'buy Bitcoin', 'sell Bitcoin', 'crypto crash',
#     'crypto bull run', 'Bitcoin price',
#     'invest in Bitcoin', 'should I buy Bitcoin', 'Bitcoin'
# ]

# keywords that are done: Bitcoin, BTC, buy Bitcoin, sell Bitcoin, crypto crash, invest in Bitcoin

# negative and positive sentiment amplifiers
# negative: sell Bitcoin, crypto crash,
# positive: BTC, Bitcoin, buy Bitcoin, crypto bull run, Bitcoin price, invest in Bitcoin, should I buy Bitcoin, crypto bull run, Bitcoin price

import pandas as pd
from pytrends.request import TrendReq
import os
import time
import random
from datetime import date, timedelta

def get_date_chunks(start_date_str, end_date_str, months_per_chunk=6):
    start_date = pd.to_datetime(start_date_str)
    end_date = pd.to_datetime(end_date_str)

    chunks = []
    current_start = start_date
    while current_start < end_date:
        current_end = current_start + pd.DateOffset(months=months_per_chunk) - timedelta(days=1)
        if current_end > end_date:
            current_end = end_date

        timeframe = f"{current_start.strftime('%Y-%m-%d')} {current_end.strftime('%Y-%m-%d')}"
        chunks.append(timeframe)
        current_start = current_end + timedelta(days=1)

    return chunks


# --- Configuration ---
# Initialize TrendReq - Use the corrected version without retry args
# Adding ssl_verify=False and requests_args might help with certain connection issues
# especially on specific network configurations or Python versions
try:
    pytrends = TrendReq(hl='en-US', tz=360)
    # Optional: Add workaround for potential SSL issues if needed
    # python_version = sys.version_info
    # if python_version.major == 3 and python_version.minor >= 9: # Example condition
    #     print("Applying requests_args workaround for potential SSL issues...")
    #     pytrends = TrendReq(hl='en-US', tz=360,
    #                         requests_args={'ssl_verify': False})
except Exception as e:
    print(f"Error initializing TrendReq: {e}")
    # Consider adding exit() or further error handling if initialization fails
    exit()

keyword = 'should I buy Bitcoin'  # Single keyword

# Timeframe
start_date = '2021-01-01'
end_date = '2024-12-31'  # Data up to end of 2024

# Create time chunks for daily data (e.g., 6 months)
timeframe_chunks = get_date_chunks(start_date, end_date, months_per_chunk=6)

print(f"Fetching daily data for keyword: '{keyword}'")
print(f"Total time chunks: {len(timeframe_chunks)}")

# --- Data Collection ---
all_daily_data = pd.DataFrame()  # Master dataframe for all results

for i, timeframe in enumerate(timeframe_chunks):
    print(f"\n----- Processing Time Chunk {i + 1}/{len(timeframe_chunks)}: {timeframe} -----")

    retries = 3  # Retries per chunk
    while retries > 0:
        try:
            pytrends.build_payload(
                kw_list=[keyword],  # Pass keyword as a list
                cat=0,
                timeframe=timeframe,
                geo='',
                gprop=''
            )
            print(f"  Payload built for chunk {i + 1}. Fetching data...")
            # Short delay after build_payload before requesting data
            time.sleep(random.uniform(2, 5))

            daily_data = pytrends.interest_over_time()
            print(f"  Data received for chunk {i + 1}.")

            if not daily_data.empty:
                if 'isPartial' in daily_data.columns:
                    daily_data = daily_data.drop(columns=['isPartial'])

                # Ensure the keyword column exists (sometimes it might be missing if value is 0?)
                if keyword not in daily_data.columns:
                    print(f"  Keyword '{keyword}' column missing in received data for this chunk, adding as 0.")
                    daily_data[keyword] = 0  # Add the column filled with 0 if it's missing

                # Append data for this chunk
                all_daily_data = pd.concat([all_daily_data, daily_data])
                print(f"    Success for chunk {i + 1}")
                break  # Success, exit retry loop for this chunk

            else:
                print(f"    No data returned for chunk {i + 1}")
                # Decide if you want to retry on empty data or just move on
                break  # Moving on if no data returned

        except Exception as e:
            retries -= 1
            print(f"    Error fetching data for chunk {i + 1}: {e}")
            # Check for specific frequent error types
            if "429" in str(e) or "response code" in str(e).lower() or "too many requests" in str(e).lower():
                # Longer wait for rate limiting
                wait_time = random.uniform(60, 120) * (4 - retries)  # Increase wait time on subsequent retries
                print(
                    f"    Rate limit suspected. Waiting {wait_time:.2f}s before retrying ({retries} retries left)...")
                time.sleep(wait_time)
            elif "timeout" in str(e).lower():
                # Moderate wait for timeouts
                wait_time = random.uniform(30, 60) * (4 - retries)
                print(f"    Timeout suspected. Waiting {wait_time:.2f}s before retrying ({retries} retries left)...")
                time.sleep(wait_time)
            else:
                # Generic wait for other errors
                wait_time = random.uniform(20, 40)
                print(f"    Waiting {wait_time:.2f}s before retrying ({retries} retries left)...")
                time.sleep(wait_time)

        if retries == 0:
            print(f"    Failed to fetch data for chunk {i + 1} after multiple retries.")

    # Longer delay between processing time chunks to be polite to the API
    if i < len(timeframe_chunks) - 1:  # Don't sleep after the last chunk
        inter_chunk_sleep = random.uniform(15, 30)  # Adjust sleep time as needed
        print(f"\nSleeping for {inter_chunk_sleep:.2f}s before next time chunk...\n")
        time.sleep(inter_chunk_sleep)

# --- Data Processing & Saving ---
print("\n--- Final Data Processing ---")

if not all_daily_data.empty:
    # Sort by date index (important after concatenating chunks)
    all_daily_data = all_daily_data.sort_index()

    # Remove potential duplicate date rows (if chunks overlapped slightly)
    # Keep the first occurrence
    all_daily_data = all_daily_data[~all_daily_data.index.duplicated(keep='first')]

    # Ensure the keyword column exists finally (might be empty df if all chunks failed)
    if keyword not in all_daily_data.columns:
        print(f"Warning: Keyword '{keyword}' column not found in final data.")
        all_daily_data[keyword] = pd.NA  # Add it as NA

    # Optional: Fill any remaining NaNs if necessary (e.g., if some dates within chunks had no data)
    # all_daily_data[keyword] = all_daily_data[keyword].fillna(0) # Example: fill with 0

    print(f"\nFinal DataFrame shape: {all_daily_data.shape}")
    print(f"Date range: {all_daily_data.index.min()} to {all_daily_data.index.max()}")

    # Save output
    output_dir = 'gtrends_data/google_trends_output_daily_single'
    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    csv_path = os.path.join(output_dir, f'{keyword}_trend_daily_{timestamp}.csv')
    json_path = os.path.join(output_dir, f'{keyword}_trend_daily_{timestamp}.json')

    all_daily_data.to_csv(csv_path)
    all_daily_data.to_json(json_path, orient='index', date_format='iso')

    print("\nData saved to:")
    print(f"- CSV: {csv_path}")
    print(f"- JSON: {json_path}")

else:
    print("\nNo data was collected. Output files not saved.")