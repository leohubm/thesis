import os
import pandas as pd
import re
from datetime import datetime
import string
# import nltk # No longer needed if only preprocessing
# from nltk.sentiment.vader import SentimentIntensityAnalyzer # REMOVED VADER

# --- VADER Lexicon Check Removed ---
# try:
#     nltk.data.find('sentiment/vader_lexicon.zip')
#     print("VADER lexicon found.")
# except LookupError:
#     nltk.download('vader_lexicon')
# --- VADER Lexicon Check Removed ---

FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_submissions.csv' # Adjust path if needed

TIMESTAMP_COLUMN = 'created'
TITLE_COLUMN = 'title'
BODY_COLUMN = 'text'
# Define columns you want to keep from the original data for EDA
OUTPUT_ORIGINAL_COLS = ['author', 'score', 'link']

# filtering for r/CryptoCurrency
KEYWORDS = ['bitcoin', 'btc', 'satoshi', 'lightning network', 'ordinals']


# setup for preprocessing
url_pattern = re.compile(r'http\S+|www\.\S+')
punctuation = string.punctuation
translate_table = str.maketrans('', '', punctuation)
keyword_pattern = r"\b(?:" + "|".join(KEYWORDS) + r")\b"
# vader = SentimentIntensityAnalyzer() # REMOVED VADER INITIALIZATION

def clean_text(text):
    """Cleans text: lowercases, removes URLs, punctuation, and extra whitespace."""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = url_pattern.sub('', text) # Remove URLs first
    text = text.translate(translate_table) # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip() # Normalize whitespace
    return text

# --- Main Processing ---
print(f"Starting processing of '{os.path.basename(FILE_PATH)}'")

# Initialize empty DataFrame for the final result
final_df = pd.DataFrame()
initial_row_count_read = 0 # To store the count after reading

try:
    # Step 1: Read the entire CSV file
    print("Reading CSV file...")
    df = pd.read_csv(
        FILE_PATH,
        sep=',',              # set separator of the csv file
        encoding='utf-8',
        on_bad_lines='skip',  # skip problematic lines
        # dtype for known text columns to help parsing & memory
        dtype={TITLE_COLUMN: str, BODY_COLUMN: str, 'author': str, 'link': str, 'url': str},
        low_memory=False # Set to False if encountering dtype warnings, but may use more memory
    )
    initial_row_count_read = len(df)
    print(f"Successfully read file into memory. Initial shape: {df.shape}")

    # Step 2: Combine 'title' and 'text' into 'text_to_analyze' and clean it
    print("Cleaning and combining text...")
    # Ensure columns exist before trying to access them
    title_col_present = TITLE_COLUMN in df.columns
    body_col_present = BODY_COLUMN in df.columns

    if title_col_present and body_col_present:
        df['text_to_analyze'] = (df[TITLE_COLUMN].fillna('') + ' ' + df[BODY_COLUMN].fillna('')).apply(clean_text)
    elif title_col_present:
        print(f"Warning: Missing '{BODY_COLUMN}'. Using only '{TITLE_COLUMN}'.")
        df['text_to_analyze'] = df[TITLE_COLUMN].fillna('').apply(clean_text)
    elif body_col_present:
        print(f"Warning: Missing '{TITLE_COLUMN}'. Using only '{BODY_COLUMN}'.")
        df['text_to_analyze'] = df[BODY_COLUMN].fillna('').apply(clean_text)
    else:
        print(f"Error: Missing both '{TITLE_COLUMN}' and '{BODY_COLUMN}'. Cannot create 'text_to_analyze'.")
        # Handle error appropriately - perhaps exit or create an empty column
        df['text_to_analyze'] = '' # Create empty column to avoid later KeyErrors

    # Step 3: Filter for Bitcoin-related content using keywords
    print("Filtering by keywords...")
    initial_rows_before_keyword_filter = len(df)
    # Apply filter only if 'text_to_analyze' column was created and is not empty
    if 'text_to_analyze' in df.columns and not df['text_to_analyze'].empty:
        # Ensure the pattern is applied correctly, case-insensitively
        df = df[df['text_to_analyze'].str.contains(keyword_pattern, case=False, na=False, regex=True)]
    print(f"Rows after keyword filter: {len(df)} (removed {initial_rows_before_keyword_filter - len(df)})")

    # Step 4: Filter out empty, deleted/removed, or too-short content
    print("Filtering by content length and specific markers...")
    initial_rows_before_content_filter = len(df)
    if 'text_to_analyze' in df.columns:
        # Filter out specific markers like '[removed]' or '[deleted]'
        df = df[~df['text_to_analyze'].isin(['', '[removed]', '[deleted]'])]
        # Filter out entries that become too short after cleaning
        df = df[df['text_to_analyze'].str.len() >= 5] # Keep the minimum length check
    print(f"Rows after content/length filter: {len(df)} (removed {initial_rows_before_content_filter - len(df)})")

    # Check if DataFrame is empty after filtering BEFORE proceeding
    if df.empty:
        print("\n--- No data remaining after applying keyword and content filters. ---")
    else:
        # Step 5: Convert timestamp
        print("Converting timestamps...")
        if TIMESTAMP_COLUMN in df.columns:
            # Attempt conversion, coercing errors to NaT (Not a Time)
            df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN], errors='coerce')

            # Report how many conversions failed
            nat_count_after_coerce = df[TIMESTAMP_COLUMN].isna().sum()
            if nat_count_after_coerce > 0:
                print(f"   Warning: {nat_count_after_coerce} out of {len(df)} rows had unrecognizable timestamp formats and were set to NaT.")

            # Drop rows where conversion resulted in NaT
            initial_rows_before_ts_drop = len(df)
            df.dropna(subset=[TIMESTAMP_COLUMN], inplace=True)
            rows_dropped_ts = initial_rows_before_ts_drop - len(df)
            if rows_dropped_ts > 0:
                print(f"   Dropped {rows_dropped_ts} rows due to invalid timestamps.")
            print(f"Rows after timestamp conversion and cleanup: {len(df)}")
        else:
            print(f"Warning: Timestamp column '{TIMESTAMP_COLUMN}' not found. Skipping timestamp conversion.")

        # --- VADER Step Removed ---
        # Step 6: Apply VADER Sentiment Analysis - THIS BLOCK IS ENTIRELY REMOVED
        # print("applying VADER")
        # if 'text_to_analyze' in df.columns:
        #     vader_scores = df['text_to_analyze'].apply(vader.polarity_scores)
        #     vader_df = pd.json_normalize(vader_scores).add_prefix('vader_')
        #     vader_df.index = df.index # Align index before concatenation
        #     df = pd.concat([df, vader_df], axis=1)
        # else:
        #     print("Warning: 'text_to_analyze' column not found for VADER.")
        # --- VADER Step Removed ---


        # Check again if empty after dropping NaT timestamps
        if df.empty:
             print("\n--- No data remaining after dropping invalid timestamps. ---")
        else:
            # Step 6 (was 7): Select and prepare final output columns
            print("Selecting final columns for output...")
            final_output_columns = []

            # Add desired original columns if they exist
            for col in OUTPUT_ORIGINAL_COLS:
                if col in df.columns:
                    final_output_columns.append(col)
                else:
                    print(f"Warning: Requested original column '{col}' not found in the DataFrame.")

            # Add timestamp column if it exists and was processed
            if TIMESTAMP_COLUMN in df.columns:
                 final_output_columns.append(TIMESTAMP_COLUMN)

            # Add the cleaned text column if it exists
            if 'text_to_analyze' in df.columns:
                 final_output_columns.append('text_to_analyze')

            # --- VADER Columns Selection Removed ---
            # final_output_columns.extend([col for col in df.columns if col.startswith('vader_')])
            # --- VADER Columns Selection Removed ---

            # Create the final DataFrame with only the selected columns that actually exist
            existing_final_cols = [col for col in final_output_columns if col in df.columns]
            if existing_final_cols:
                 print(f"Final columns selected: {existing_final_cols}")
                 final_df = df[existing_final_cols].copy() # Use .copy() to avoid SettingWithCopyWarning
            else:
                 print("Error: No columns available for final output after selection.")


except MemoryError:
    print("\n--- MEMORY ERROR ---")
    print("The CSV file is likely too large to load into memory all at once.")
    print("Consider using chunk processing (pd.read_csv with chunksize).")
except KeyError as e:
     # This error means a column name used directly (like in filters or operations) was incorrect/missing
     print(f"\n--- ERROR: Missing Column During Processing ---")
     print(f"Tried to access a column that doesn't exist: {e}")
     import traceback
     traceback.print_exc()
except Exception as e:
    print(f"\n--- An Unexpected Error Occurred During Processing ---")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    import traceback
    traceback.print_exc()


# --- Saving the Preprocessed Data ---
if not final_df.empty:
    print("\nPreprocessing complete. Saving results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(FILE_PATH)
    dir_name = os.path.dirname(FILE_PATH)
    if not dir_name: dir_name = '../..'  # Handle case where file is in the current directory

    # Adjust filename to reflect only preprocessing
    output_filename = base_name.replace('.csv', f'_bitcoin_filtered_preprocessed_{timestamp}.csv')
    output_path = os.path.join(dir_name, output_filename)

    try:
        final_df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n--- Processing Summary ---")
        print(f"Initial rows read (approx): {initial_row_count_read}") # Use the stored count
        # Note: df might not exist if reading failed early on. Handle this.
        # intermediate_rows = len(df) if 'df' in locals() and df is not None else 'N/A'
        # print(f"Rows before final selection: {intermediate_rows}")
        print(f"Final rows kept after all processing & filtering: {len(final_df)}")
        print(f"Final DataFrame columns: {final_df.columns.tolist()}")
        print(f"Final DataFrame shape: {final_df.shape}")
        print(f"\nSuccessfully saved preprocessed data to:\n{output_path}")
    except Exception as e:
        print(f"\n--- Error Saving File ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
else:
    # This message covers cases where df became empty during filtering or if final selection failed
    print("\nFinal DataFrame is empty. No output file created.")
    print("This could be due to filters removing all data, timestamp issues, or an error during processing.")

print("\nScript finished.")