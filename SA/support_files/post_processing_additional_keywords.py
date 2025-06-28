# Post Processing for strategy refinement

import os
import pandas as pd
import re
from datetime import datetime
import string
import traceback

#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_submissions.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_comments.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_submissions.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_comments.csv'

#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_submissions.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\CryptoCurrency_comments.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_submissions.csv'
#FILE_PATH = r'C:\Users\Leo Hubmann\Desktop\BachelorThesis_data\Bitcoin_comments.csv'

TIMESTAMP_COLUMN = 'created'

KEYWORDS = [
  'lost', 'issue', 'address', 'password', 'recovery'
]
