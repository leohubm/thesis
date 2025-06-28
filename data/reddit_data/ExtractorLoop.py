# This script converts all .zst files in a specified input folder to .csv files in an output folder.
# It processes only data between July 1, 2015, and October 31, 2021.
# The resulting files may be quite large and might not be suitable for opening in standard CSV readers like Excel.
# credit, adjusted script Marco Hafid

import zstandard
import os
import json
import csv
from datetime import datetime
import logging.handlers
import glob

# Input and output paths
input_folder = r"C:\Users\Leo Hubmann\Downloads\reddit\subreddits24"
output_folder = r"C:\Users\Leo Hubmann\Desktop\BachelorThesis_data"

log = logging.getLogger("bot")
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

def read_and_decode(reader, chunk_size, max_window_size, previous_chunk=None, bytes_read=0):
    chunk = reader.read(chunk_size)
    bytes_read += chunk_size
    if previous_chunk is not None:
        chunk = previous_chunk + chunk
    try:
        return chunk.decode()
    except UnicodeDecodeError:
        if bytes_read > max_window_size:
            raise UnicodeError(f"Unable to decode frame after reading {bytes_read:,} bytes")
        return read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)

def read_lines_zst(file_name):
    with open(file_name, 'rb') as file_handle:
        buffer = ''
        reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(file_handle)
        while True:
            chunk = read_and_decode(reader, 2**27, (2**29) * 2)
            if not chunk:
                break
            lines = (buffer + chunk).split("\n")

            for line in lines[:-1]:
                yield line, file_handle.tell()

            buffer = lines[-1]
        reader.close()

if __name__ == "__main__":
    # Get list of .zst files in the input folder
    file_list = glob.glob(os.path.join(input_folder, '*.zst'))

    # Specify date range
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2024, 12, 31, 23, 59, 59)

    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)

    for input_file_path in file_list:
        # For each file, process it
        log.info(f"Processing file: {input_file_path}")

        # Get base filename and set output file path
        base_name = os.path.basename(input_file_path)
        output_file_name = os.path.splitext(base_name)[0] + '.csv'
        output_file_path = os.path.join(output_folder, output_file_name)

        log.info(f"Output will be saved to: {output_file_path}")

        # Determine if the file contains submissions or comments based on the filename
        if 'submission' in base_name.lower():
            is_submission = True
            fields = ["author", "title", "score", "created", "link", "text", "url"]
        elif 'comment' in base_name.lower():
            is_submission = False
            fields = ["author", "score", "created", "link", "body"]
        else:
            # If the file name doesn't specify, you might want to skip or handle it differently
            log.warning(f"Unable to determine data type for file {base_name}, skipping.")
            continue  # Skip this file

        file_size = os.stat(input_file_path).st_size
        file_lines, bad_lines = 0, 0
        line, created = None, None

        with open(output_file_path, "w", encoding='utf-8', newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(fields)

            try:
                for line, file_bytes_processed in read_lines_zst(input_file_path):
                    file_lines += 1
                    try:
                        obj = json.loads(line)
                        created = datetime.utcfromtimestamp(int(obj['created_utc']))

                        # Check if the date is within the specified range
                        if not (start_date <= created <= end_date):
                            continue  # Skip lines outside the date range

                        output_obj = []
                        for field in fields:
                            if field == "created":
                                value = datetime.fromtimestamp(int(obj['created_utc'])).strftime("%Y-%m-%d %H:%M")
                            elif field == "link":
                                if 'permalink' in obj:
                                    value = f"https://www.reddit.com{obj['permalink']}"
                                else:
                                    # For comments, construct the permalink
                                    value = f"https://www.reddit.com/r/{obj.get('subreddit', '')}/comments/{obj.get('link_id', 't3_')[3:]}/_/{obj.get('id', '')}/"
                            elif field == "author":
                                value = f"u/{obj.get('author', '[deleted]')}"
                            elif field == "text":
                                value = obj.get('selftext', '')
                            else:
                                value = obj.get(field, '')

                            output_obj.append(str(value).encode("utf-8", errors='replace').decode())
                        writer.writerow(output_obj)
                    except KeyError as err:
                        bad_lines += 1
                        log.debug(f"KeyError for line {file_lines}: Missing key {err}")
                    except json.JSONDecodeError:
                        bad_lines += 1
                        log.debug(f"JSONDecodeError for line {file_lines}")
                    except Exception as err:
                        bad_lines += 1
                        log.debug(f"Error processing line {file_lines}: {err}")
                    if file_lines % 100000 == 0:
                        created_str = created.strftime('%Y-%m-%d %H:%M:%S') if created else ''
                        progress = (file_bytes_processed / file_size) * 100
                        log.info(f"{created_str} : {file_lines:,} lines processed : {bad_lines:,} bad lines : {progress:.0f}% done")
            except Exception as err:
                log.error(f"Error processing file {input_file_path}: {err}")
            finally:
                log.info(f"Completed: {file_lines:,} lines processed with {bad_lines:,} bad lines for file {input_file_path}")
