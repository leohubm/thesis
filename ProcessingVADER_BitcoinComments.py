import os
import pandas as pd
import re
from datetime import datetime
import string
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import traceback

FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_comments.csv'

TIMESTAMP_COLUMN = 'created'
TEXT_COLUMN = 'body'
OUTPUT_ORIGINAL_COLS = ['author', 'score', 'link']

# KEYWORDS = ['bitcoin', 'btc']

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
    print("VADER lexicon found.")
except LookupError:
    print("VADER lexicon not found. Downloading...")
    nltk.download('vader_lexicon')
    print("VADER lexicon downloaded.")

# --- Preprocessing Setup ---
url_pattern = re.compile(r'http\S+|www\.\S+')
punctuation = string.punctuation
# Create a translation table to remove punctuation
translate_table = str.maketrans('', '', punctuation)
# Create a regex pattern for keywords (case-insensitive word boundaries)
#keyword_pattern = r"\b(?:" + "|".join(map(re.escape, KEYWORDS)) + r")\b"
vader = SentimentIntensityAnalyzer()

def clean_text(text):
    """Cleans text data: converts to lowercase, removes URLs, punctuation, and extra whitespace."""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = url_pattern.sub('', text)        # Remove URLs
    text = text.translate(translate_table) # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip() # Replace multiple spaces with single, trim ends
    return text

print(f"Processing file: '{os.path.basename(FILE_PATH)}'")

final_df = pd.DataFrame()
df = None # Initialize df to None for better error checking later

try:
    # Step 1: Read the entire CSV file
    print("Reading CSV file...")
    df = pd.read_csv(
        FILE_PATH,
        sep=',',              # Separator for the CSV file
        encoding='utf-8',
        on_bad_lines='skip',  # Skip lines that cause parsing errors
        # Define dtypes for known text columns to optimize memory and prevent parsing issues
        # Adjusted for the comments CSV structure
        dtype={TEXT_COLUMN: str, 'author': str, 'link': str},
        low_memory=False      # Can help with mixed types, but use more memory
    )
    print(f"Successfully read file. Initial shape: {df.shape}")

    # Step 2: Prepare and clean the text to analyze from the 'body' column
    print("Cleaning text...")
    if TEXT_COLUMN in df.columns:
        # Directly use the TEXT_COLUMN ('body') and apply cleaning
        df['text_to_analyze'] = df[TEXT_COLUMN].apply(clean_text)
        print(f"   'text_to_analyze' column created from '{TEXT_COLUMN}'.")
    else:
        print(f"Error: Required text column '{TEXT_COLUMN}' not found in the DataFrame. Cannot proceed with analysis.")
        # Optionally raise an error or exit if this column is critical
        raise KeyError(f"Required column '{TEXT_COLUMN}' missing from input file.")

    # # Step 3: Filter for keyword-related content using keywords
    # print(f"Filtering by keywords: {KEYWORDS}...")
    # initial_rows = len(df)
    # # Filter based on the cleaned text
    # df = df[df['text_to_analyze'].str.contains(keyword_pattern, case=False, regex=True, na=False)]
    # print(f"Rows after keyword filter: {len(df)} (removed {initial_rows - len(df)})")

    # Step 4: Filter out empty, deleted/removed, or too-short content
    print("Filtering by content length and specific strings...")
    initial_rows = len(df)
    df = df[~df['text_to_analyze'].isin(['', '[removed]', '[deleted]'])] # Filter specific strings
    df = df[df['text_to_analyze'].str.len() >= 5] # Filter based on minimum length
    print(f"Rows after content/length filter: {len(df)} (removed {initial_rows - len(df)})")

    if df.empty:
        print("\n--- No data remaining after applying text and keyword filters. ---")
    else:
        # Step 5: Convert timestamp column
        print("Converting timestamps...")
        if TIMESTAMP_COLUMN in df.columns:
            # Directly attempt conversion, letting pandas infer the format
            # This assumes the 'created' column contains recognizable date/time strings
            df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN], errors='coerce')
            print("   Attempted conversion letting pandas infer the date/time format.")

            # Check how many values could not be converted
            nat_count_initial = df[TIMESTAMP_COLUMN].isna().sum()
            print(f"   Number of invalid timestamp values found (became NaT): {nat_count_initial} (out of {len(df)})")
            if nat_count_initial > 0:
                 print("      (These rows with invalid timestamps will be dropped)")

            # Drop rows where timestamp conversion failed (resulted in NaT)
            initial_rows_before_drop = len(df)
            df.dropna(subset=[TIMESTAMP_COLUMN], inplace=True)
            print(f"   Rows after dropping invalid timestamps: {len(df)} (removed {initial_rows_before_drop - len(df)})")
        else:
            print(f"Warning: Timestamp column '{TIMESTAMP_COLUMN}' not found. Skipping timestamp conversion.")

        # Check again if empty after dropping NaT timestamps
        if df.empty:
             print("\n--- No data remaining after dropping invalid timestamps. ---")
        else:
            # Step 6: Apply VADER Sentiment Analysis
            print("Applying VADER sentiment analysis...")
            # Apply VADER to the cleaned text column
            vader_scores = df['text_to_analyze'].apply(vader.polarity_scores)
            # Normalize the dictionary output into separate columns
            vader_df = pd.json_normalize(vader_scores).add_prefix('vader_')
            # Align index before concatenation to prevent misalignment issues
            vader_df.index = df.index
            df = pd.concat([df, vader_df], axis=1)
            print("   VADER scores calculated and added.")

            # Step 7: Select and prepare final output columns
            print("Selecting final columns for output...")
            final_output_columns = []

            # Add original columns specified in OUTPUT_ORIGINAL_COLS if they exist
            for col in OUTPUT_ORIGINAL_COLS:
                if col in df.columns:
                    final_output_columns.append(col)
                else:
                    print(f"   Warning: Requested output column '{col}' not found in DataFrame.")

            # Add timestamp column if it exists and was processed
            if TIMESTAMP_COLUMN in df.columns:
                 final_output_columns.append(TIMESTAMP_COLUMN)

            # Add the cleaned text column
            if 'text_to_analyze' in df.columns:
                 final_output_columns.append('text_to_analyze')

            # Add all VADER score columns (compound, neg, neu, pos)
            final_output_columns.extend([col for col in df.columns if col.startswith('vader_')])

            # Ensure only existing columns are selected
            existing_final_cols = [col for col in final_output_columns if col in df.columns]

            if existing_final_cols:
                 final_df = df[existing_final_cols]
                 print(f"   Final columns selected: {existing_final_cols}")
            else:
                 print("Error: No columns available for final output after processing.")


except MemoryError:
    print("\n--- MEMORY ERROR ---")
    print("The script failed to load or process the CSV file due to insufficient memory.")
    print("Consider processing the file in chunks if it's very large.")
except KeyError as e:
     # This error means a column name used was incorrect/missing
     print(f"\n--- ERROR: Missing Column During Processing ---")
     print(f"The script tried to access a column name that does not exist: '{e}'.")
     print("Please check the column names in your CSV and the script's configuration (e.g., TEXT_COLUMN).")
     traceback.print_exc()
except Exception as e:
    print(f"\n--- An Unexpected Error Occurred During Processing ---")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    traceback.print_exc()


# --- Save Results ---
if not final_df.empty:
    print("\nProcessing complete. Preparing to save results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(FILE_PATH)
    dir_name = os.path.dirname(FILE_PATH)
    # Handle case where the script is run in the same directory as the file
    if not dir_name: dir_name = '.'

    # Construct a descriptive output filename
    output_filename = base_name.replace('.csv', f'_filtered_vader_{timestamp}.csv')
    output_path = os.path.join(dir_name, output_filename)

    try:
        final_df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n--- Processing Summary ---")
        if df is not None: # Check if df was successfully created
             print(f"Initial rows read (approx, excluding skipped bad lines): {df.shape[0] if df is not None else 'N/A'}")
        else:
             print("Initial rows read: N/A (Error during file reading)")
        print(f"Rows kept after all processing & filtering: {len(final_df)}")
        print(f"Final DataFrame columns: {final_df.columns.tolist()}")
        print(f"Final DataFrame shape: {final_df.shape}")
        print(f"\nSuccessfully saved results to:\n{output_path}")
    except Exception as e:
        print(f"\n--- Error Saving File ---")
        print(f"Could not save the results to '{output_path}'.")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
else:
    # This block executes if final_df is empty after the try/except block
    print("\n--- No Results ---")
    print("The final DataFrame is empty. No output file was created.")
    print("This could be because:")
    print("  - All rows were filtered out by the keyword, content length, or timestamp filters.")
    print("  - An error occurred during processing before the final DataFrame could be populated.")
    print("  - The input file itself was empty or contained no relevant data.")

print("\nScript finished.")