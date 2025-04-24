import os
import pandas as pd
import re
from datetime import datetime
import string
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
    print("VADER lexicon found.")
except LookupError:
    nltk.download('vader_lexicon')

FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_submissions.csv'

TIMESTAMP_COLUMN = 'created'
TITLE_COLUMN = 'title'
BODY_COLUMN = 'text'
OUTPUT_ORIGINAL_COLS = ['author', 'score', 'link']

# filtering for r/CryptoCurrency
KEYWORDS = ['bitcoin', 'btc']


# setup for preprocessing
url_pattern = re.compile(r'http\S+|www\.\S+')
punctuation = string.punctuation
translate_table = str.maketrans('', '', punctuation)
keyword_pattern = r"\b(?:" + "|".join(KEYWORDS) + r")\b"
vader = SentimentIntensityAnalyzer()

def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = url_pattern.sub('', text)
    text = text.translate(translate_table)
    text = re.sub(r'\s+', ' ', text).strip()
    return text



# processing
print(f"processing of '{os.path.basename(FILE_PATH)}'")

# initialize empty DataFrame for the final result
final_df = pd.DataFrame()

try:
    # step 1: read the entire CSV file
    df = pd.read_csv(
        FILE_PATH,
        sep=',',              # set separator of the csv file
        encoding='utf-8',
        on_bad_lines='skip',  # skip problematic lines
        # dtype for known text columns to help parsing & memory
        dtype={TITLE_COLUMN: str, BODY_COLUMN: str, 'author': str, 'link': str, 'url': str},
        low_memory=False
    )
    print(f"Successfully read file into memory. Initial shape: {df.shape}")

    # step 2: combine 'title' and 'text' into 'text_to_analyze' and clean it
    print("Cleaning text...")

    if TITLE_COLUMN in df.columns and BODY_COLUMN in df.columns:
        df['text_to_analyze'] = (df[TITLE_COLUMN].fillna('') + ' ' + df[BODY_COLUMN].fillna('')).apply(clean_text)
    else:
        print(f"Error: Missing '{TITLE_COLUMN}' or '{BODY_COLUMN}' in the DataFrame.")
        df['text_to_analyze'] = ''

    # step 3: filter for Bitcoin-related content using keywords
    print("Filtering by keywords...")
    initial_rows = len(df)
    # apply filter only if 'text_to_analyze' column was created
    if 'text_to_analyze' in df.columns:
        df = df[df['text_to_analyze'].str.contains(keyword_pattern, case=False, na=False)]
    print(f"Rows after keyword filter: {len(df)} (removed {initial_rows - len(df)})")

    # step 4: filter out empty, deleted/removed, or too-short content
    print("Filtering by content/length...")
    initial_rows = len(df)
    if 'text_to_analyze' in df.columns:
        df = df[~df['text_to_analyze'].isin(['', '[removed]', '[deleted]'])]
        df = df[df['text_to_analyze'].str.len() >= 5]
    print(f"Rows after content/length filter: {len(df)} (removed {initial_rows - len(df)})")

    # check if DataFrame is empty after filtering BEFORE proceeding
    if df.empty:
        print("\n--- No data remaining after applying filters. ---")
    else:
        # step 5: convert timestamp
        print("Converting timestamps...")
        if TIMESTAMP_COLUMN in df.columns:

            df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN], errors='coerce')

            nat_count_after_coerce = df[TIMESTAMP_COLUMN].isna().sum()
            print(f"   number of NaT values after coercion: {nat_count_after_coerce} (out of {len(df)})")
            if nat_count_after_coerce > 0:
                 print("    (NaT values indicate rows where the string was not a recognizable date/time format)")

            # drop rows where conversion still failed (genuinely bad data)
            initial_rows = len(df)
            df.dropna(subset=[TIMESTAMP_COLUMN], inplace=True) # Keep this active
            print(f"rows after dropping invalid timestamps: {len(df)} (removed {initial_rows - len(df)})")
        else:
            print(f"Warning: Timestamp column '{TIMESTAMP_COLUMN}' not found.")

        # check again if empty after dropping NaT timestamps
        if df.empty:
             print("\n--- No data remaining after dropping invalid timestamps. ---")
        else:
            # step 6: Apply VADER Sentiment Analysis
            print("applying VADER")
            if 'text_to_analyze' in df.columns:
                vader_scores = df['text_to_analyze'].apply(vader.polarity_scores)
                vader_df = pd.json_normalize(vader_scores).add_prefix('vader_')
                # Align index before concatenation
                vader_df.index = df.index
                df = pd.concat([df, vader_df], axis=1)
            else:
                print("Warning: 'text_to_analyze' column not found for VADER.")

            # step 7: Select and prepare final output columns
            print("Selecting final columns...")
            final_output_columns = []

            for col in OUTPUT_ORIGINAL_COLS:
                if col in df.columns:
                    final_output_columns.append(col)

            if TIMESTAMP_COLUMN in df.columns:
                 final_output_columns.append(TIMESTAMP_COLUMN)

            if 'text_to_analyze' in df.columns:
                 final_output_columns.append('text_to_analyze')

            final_output_columns.extend([col for col in df.columns if col.startswith('vader_')])


            existing_final_cols = [col for col in final_output_columns if col in df.columns]
            if existing_final_cols:
                 final_df = df[existing_final_cols]
            else:
                 print("error: No columns available for final output.")


except MemoryError:
    print("\n--- MEMORY ERROR ---")
    print("failed to load the entire CSV file into memory.")
except KeyError as e:
     # This error means a column name used directly was incorrect/missing
     print(f"\n--- ERROR: Missing Column During Processing ---")
     print(f"Tried to access column name '{e}'.")
     import traceback
     traceback.print_exc()
except Exception as e:
    print(f"\n--- An Unexpected Error Occurred During Processing ---")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    import traceback
    traceback.print_exc()


if not final_df.empty:
    print("\nProcessing complete. Saving results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(FILE_PATH)
    dir_name = os.path.dirname(FILE_PATH)
    if not dir_name: dir_name = '.'

    output_filename = base_name.replace('.csv', f'_bitcoin_filtered_vader_{timestamp}.csv')
    output_path = os.path.join(dir_name, output_filename)

    try:
        final_df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n--- Processing Summary ---")

        print(f"Initial rows read (approx, excludes rows skipped due to parsing errors): {len(df) if 'df' in locals() and df is not None else 'N/A'}")
        print(f"Rows kept after all processing & filtering: {len(final_df)}")
        print(f"Final DataFrame columns: {final_df.columns.tolist()}")
        print(f"Final DataFrame shape: {final_df.shape}")
        print(f"\nSuccessfully saved results to:\n{output_path}")
    except Exception as e:
        print(f"\n--- Error Saving File ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
else:

    print("\nFinal DataFrame is empty. No output file created (or file contains only header).")
    print("This could be due to filters removing all data or an error during processing.")

print("\nScript finished.")