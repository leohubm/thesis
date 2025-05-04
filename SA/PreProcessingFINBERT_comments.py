## check if remove due to double use

import os
import pandas as pd
import re
from datetime import datetime
import string
import traceback

#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_submissions.csv'
FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_comments.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_submissions.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_comments.csv'

TIMESTAMP_COLUMN = 'created'

# --only for submissions--
# TITLE_COLUMN = 'title'

# BODY_COLUMN = 'text'
BODY_COLUMN = 'body'

OUTPUT_ORIGINAL_COLS = ['author', 'score', 'link']

KEYWORDS = ['bitcoin', 'btc']

# --Advanced Keyword-Filter for comparison--
#KEYWORDS = ['bitcoin', 'btc']

# --- Preprocessing Setup for FinBERT ---
url_pattern = re.compile(r'http\S+|www\.\S+')
punctuation_to_remove = string.punctuation # Define punctuation to remove
# Create translation table for removing punctuation
translate_table = str.maketrans('', '', punctuation_to_remove)

# Pattern for keywords (case-insensitive word boundaries)
keyword_pattern = r"\b(?:" + "|".join(map(re.escape, KEYWORDS)) + r")\b"

# New patterns for FinBERT preprocessing
user_mention_pattern = re.compile(r'\/?u\/\w+') # Matches /u/username or u/username
subreddit_mention_pattern = re.compile(r'\/?r\/\w+') # Matches /r/subreddit or r/subreddit
# Comprehensive emoji pattern
emoji_pattern = re.compile(
    "["
    u"\U0001F600-\U0001F64F"  # emoticons
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    u"\U0001F680-\U0001F6FF"  # transport & map symbols
    u"\U0001F700-\U0001F77F"  # alchemical symbols
    u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    u"\U00002702-\U000027B0"  # Dingbats
    u"\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE)

def clean_text_for_finbert(text):
    """
    Cleans text for FinBERT:
    - Converts to lowercase.
    - Removes URLs.
    - Removes Reddit user/subreddit mentions (e.g., u/username, r/subreddit).
    - Removes emojis.
    - Removes punctuation (defined by string.punctuation).
    - Normalizes whitespace to single spaces.
    """
    if pd.isna(text):
        return ""
    text = str(text).lower()
    # 1. Remove URLs
    text = url_pattern.sub('', text)
    # 2. Remove user/subreddit mentions
    text = user_mention_pattern.sub('', text)
    text = subreddit_mention_pattern.sub('', text)
    # 3. Remove Emojis
    text = emoji_pattern.sub('', text)
    # 4. Remove Punctuation (keeps numbers)
    text = text.translate(translate_table)
    # 5. Normalize Whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- Main Processing Logic ---
print(f"Starting preprocessing of '{os.path.basename(FILE_PATH)}' (Comments Data) for FinBERT.") # Clarified title

final_df = pd.DataFrame()
initial_row_count_read = 0
df = None

try:
    # Step 1: Read the entire CSV file
    print("Reading CSV file...")
    # --- MODIFICATION START: Adjusted dtype for comments ---
    # Define dtypes, ensuring BODY_COLUMN uses the variable and TITLE_COLUMN is removed
    # Keep 'url' handling logic as before, assuming 'url' might or might not be in comments CSV
    base_dtype = {BODY_COLUMN: str, 'author': str, 'link': str}
    try:
        # Try reading with 'url' column
        read_dtype = base_dtype.copy()
        read_dtype['url'] = str
        df = pd.read_csv(
            FILE_PATH,
            sep=',',
            encoding='utf-8',
            on_bad_lines='skip',
            dtype=read_dtype, # Use updated dtype map
            low_memory=False
        )
    except ValueError as e:
         # If 'url' column causes issues (e.g., missing), try without specifying its dtype
        if 'url' in str(e):
            print("Warning: Issue reading 'url' column. Retrying without specifying its dtype.")
            read_dtype_no_url = base_dtype.copy() # Reset to base, excluding 'url'
            df = pd.read_csv(
                FILE_PATH,
                sep=',',
                encoding='utf-8',
                on_bad_lines='skip',
                dtype=read_dtype_no_url, # Use dtype without 'url'
                low_memory=False
            )
        else:
             # If error is not about 'url', re-raise it
             raise e
    # --- MODIFICATION END ---

    initial_row_count_read = len(df)
    print(f"Successfully read file. Initial shape: {df.shape}")

    # Step 2: Clean the body text and assign to 'text_to_analyze'
    print("Cleaning body text for FinBERT...") # Changed print message
    # --- MODIFICATION START: Simplified for body column only ---
    # title_col_present = TITLE_COLUMN in df.columns # This would be False now
    body_col_present = BODY_COLUMN in df.columns

    if body_col_present:
        # Directly use the BODY_COLUMN for cleaning
        print(f"Using column '{BODY_COLUMN}' for text analysis.")
        df['text_to_analyze'] = df[BODY_COLUMN].fillna('').apply(clean_text_for_finbert)
    else:
        # Handle case where even the body column is missing
        print(f"Error: Body column '{BODY_COLUMN}' not found. Cannot create 'text_to_analyze'.")
        df['text_to_analyze'] = '' # Create empty column to prevent later errors
    # --- MODIFICATION END ---

    # Step 3: Filter for keyword-related content using keywords
    print(f"Filtering by keywords: {KEYWORDS}...") # Commented out print
    # print("Skipping keyword filtering (keyword_pattern is commented out).")
    initial_rows_before_keyword_filter = len(df)
    if 'text_to_analyze' in df.columns and not df['text_to_analyze'].empty:
        # Ensure keyword_pattern is defined before using it. Since it's commented out above, this line would fail.
        df = df[df['text_to_analyze'].str.contains(keyword_pattern, case=False, na=False, regex=True)] # Commented out filtering step
    print(f"Rows after keyword filter: {len(df)} (removed {initial_rows_before_keyword_filter - len(df)})") # Commented out print
    # print(f"Rows remaining (no keyword filter applied): {len(df)}") # Added alternative print

    # Step 4: Filter out empty, deleted/removed, or too-short content
    print("Filtering by content length and specific markers...")
    initial_rows_before_content_filter = len(df)
    if 'text_to_analyze' in df.columns:
        df = df[~df['text_to_analyze'].isin(['', '[removed]', '[deleted]'])]
        # Keep a minimum length check after cleaning
        df = df[df['text_to_analyze'].str.len() >= 5]
    print(f"Rows after content/length filter: {len(df)} (removed {initial_rows_before_content_filter - len(df)})")

    # Check if DataFrame is empty after filtering
    if df.empty:
        # --- MODIFICATION START: Adjusted message slightly ---
        print("\n--- No data remaining after applying content/length filters. ---")
        # --- MODIFICATION END ---
    else:
        # Step 5: Convert timestamp (Keeping existing logic as requested)
        print("Converting timestamps...")
        if TIMESTAMP_COLUMN in df.columns:
            df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN], errors='coerce')
            nat_count_after_coerce = df[TIMESTAMP_COLUMN].isna().sum()
            if nat_count_after_coerce > 0:
                print(f"   Warning: {nat_count_after_coerce} out of {len(df)} rows had unrecognizable timestamp formats and were set to NaT.")

            initial_rows_before_ts_drop = len(df)
            df.dropna(subset=[TIMESTAMP_COLUMN], inplace=True) # Drop rows with NaT timestamps
            rows_dropped_ts = initial_rows_before_ts_drop - len(df)
            if rows_dropped_ts > 0:
                print(f"   Dropped {rows_dropped_ts} rows due to invalid timestamps.")
            print(f"Rows after timestamp conversion and cleanup: {len(df)}")
        else:
            print(f"Warning: Timestamp column '{TIMESTAMP_COLUMN}' not found. Skipping timestamp conversion.")

        # Check again if empty after dropping NaT timestamps
        if df.empty:
             print("\n--- No data remaining after dropping invalid timestamps. ---")
        else:
            # Step 6: Select and prepare final output columns
            print("Selecting final columns for output...")
            final_output_columns = []

            # Add desired original columns if they exist
            for col in OUTPUT_ORIGINAL_COLS:
                if col in df.columns:
                    final_output_columns.append(col)
                else:
                    print(f"Warning: Requested original column '{col}' not found.")

            # Add timestamp column if processed
            if TIMESTAMP_COLUMN in df.columns and df[TIMESTAMP_COLUMN].notna().any(): # Check if column exists and has non-NA values
                 final_output_columns.append(TIMESTAMP_COLUMN)

            # Add the cleaned text column for FinBERT input
            if 'text_to_analyze' in df.columns:
                 final_output_columns.append('text_to_analyze')

            # Create the final DataFrame
            existing_final_cols = [col for col in final_output_columns if col in df.columns]
            if existing_final_cols:
                 print(f"Final columns selected: {existing_final_cols}")
                 final_df = df[existing_final_cols].copy() # Use .copy()
            else:
                 print("Error: No columns available for final output.")


except MemoryError:
    print("\n--- MEMORY ERROR ---")
    print("Failed to load/process CSV due to insufficient memory.")
    print("Consider using chunk processing (pd.read_csv with chunksize) for very large files.")
except KeyError as e:
     print(f"\n--- ERROR: Missing Column During Processing ---")
     print(f"Tried to access a column that doesn't exist in the CSV or DataFrame: {e}")
     traceback.print_exc()
except Exception as e:
    print(f"\n--- An Unexpected Error Occurred During Processing ---")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    traceback.print_exc()


# --- Saving the Preprocessed Data ---
if not final_df.empty:
    print("\nPreprocessing complete. Saving results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(FILE_PATH)
    dir_name = os.path.dirname(FILE_PATH)
    if not dir_name: dir_name = '.' # Handle case where file is in the current directory

    # Adjust filename to reflect FinBERT preprocessing
    output_filename = base_name.replace('.csv', f'_finbert_preprocessed_{timestamp}.csv')
    output_path = os.path.join(dir_name, output_filename)

    try:
        final_df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n--- Processing Summary ---")
        print(f"Initial rows read (approx): {initial_row_count_read}")
        print(f"Final rows kept after all processing & filtering: {len(final_df)}")
        print(f"Final DataFrame columns: {final_df.columns.tolist()}")
        print(f"Final DataFrame shape: {final_df.shape}")
        print(f"\nSuccessfully saved FinBERT-preprocessed data to:\n{output_path}")
    except Exception as e:
        print(f"\n--- Error Saving File ---")
        print(f"Could not save file to '{output_path}'")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
else:
    # --- MODIFICATION START: Adjusted message slightly ---
    print("\nFinal DataFrame is empty. No output file created.")
    print("Verify input data and filters (content/length, timestamp).")
    # --- MODIFICATION END ---


print("\nScript finished.")