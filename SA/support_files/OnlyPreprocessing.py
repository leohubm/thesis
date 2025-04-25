import os
import pandas as pd
import re
from datetime import datetime
import string
import traceback

#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_submissions.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_comments.csv'
FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_submissions.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_comments.csv'

TIMESTAMP_COLUMN = 'created'
# !! remove TITLE_COLUMN for _comments
TITLE_COLUMN = 'title'
BODY_COLUMN = 'text'
#BODY_COLUMN = 'body'

OUTPUT_ORIGINAL_COLS = ['author', 'score', 'link']

# Filtering keywords (remains the same) !! only for r/CryptoCurrency
#KEYWORDS = ['bitcoin', 'btc']

url_pattern = re.compile(r'http\S+|www\.\S+')
punctuation_to_remove = string.punctuation

translate_table = str.maketrans('', '', punctuation_to_remove)

# !! only for r/CryptoCurrency
#keyword_pattern = r"\b(?:" + "|".join(map(re.escape, KEYWORDS)) + r")\b" # Use re.escape

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

print(f"Starting preprocessing of '{os.path.basename(FILE_PATH)}' for FinBERT.")

final_df = pd.DataFrame()
initial_row_count_read = 0 # To store the count after reading
df = None # Initialize df

try:
    # Step 1: Read the entire CSV file
    print("Reading CSV file...")
    # Ensure 'url' column exists in your CSV or remove it from dtype if not needed
    # If 'url' is not consistently present, remove it from dtype to avoid potential errors
    try:
        df = pd.read_csv(
            FILE_PATH,
            sep=',',
            encoding='utf-8',
            on_bad_lines='skip',
            dtype={TITLE_COLUMN: str, BODY_COLUMN: str, 'author': str, 'link': str, 'url': str}, # Check if 'url' column exists
            low_memory=False
        )
    except ValueError as e:
        # If 'url' column causes issues (e.g., missing), try without specifying its dtype
        if 'url' in str(e):
            print("Warning: Issue reading 'url' column. Retrying without specifying its dtype.")
            df = pd.read_csv(
                FILE_PATH,
                sep=',',
                encoding='utf-8',
                on_bad_lines='skip',
                dtype={TITLE_COLUMN: str, BODY_COLUMN: str, 'author': str, 'link': str}, # Removed 'url' from dtype
                low_memory=False
            )
        else:
            raise e # Re-raise other ValueErrors

    initial_row_count_read = len(df)
    print(f"Successfully read file. Initial shape: {df.shape}")

    # Step 2: Combine 'title' and 'text' into 'text_to_analyze' and apply FinBERT cleaning
    print("Cleaning and combining text for FinBERT...")
    title_col_present = TITLE_COLUMN in df.columns
    body_col_present = BODY_COLUMN in df.columns

    if title_col_present and body_col_present:
        # Combine title and body, fill NaN with empty string before combining
        df['text_to_analyze'] = (df[TITLE_COLUMN].fillna('') + ' ' + df[BODY_COLUMN].fillna('')).apply(clean_text_for_finbert)
    elif title_col_present:
        print(f"Warning: Missing '{BODY_COLUMN}'. Using only '{TITLE_COLUMN}'.")
        df['text_to_analyze'] = df[TITLE_COLUMN].fillna('').apply(clean_text_for_finbert)
    elif body_col_present:
        print(f"Warning: Missing '{TITLE_COLUMN}'. Using only '{BODY_COLUMN}'.")
        df['text_to_analyze'] = df[BODY_COLUMN].fillna('').apply(clean_text_for_finbert)
    else:
        print(f"Error: Missing both '{TITLE_COLUMN}' and '{BODY_COLUMN}'. Cannot create 'text_to_analyze'.")
        df['text_to_analyze'] = '' # Create empty column

    # !! only for r/CryptoCurrency
    # Step 3: Filter for keyword-related content using keywords
    # print(f"Filtering by keywords: {KEYWORDS}...")
    # initial_rows_before_keyword_filter = len(df)
    # if 'text_to_analyze' in df.columns and not df['text_to_analyze'].empty:
    #     df = df[df['text_to_analyze'].str.contains(keyword_pattern, case=False, na=False, regex=True)]
    # print(f"Rows after keyword filter: {len(df)} (removed {initial_rows_before_keyword_filter - len(df)})")

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
        print("\n--- No data remaining after applying keyword and content filters. ---")
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
    print("\nFinal DataFrame is empty. No output file created.")
    print("Verify filters, timestamp formats, and potential errors during processing.")

print("\nScript finished.")