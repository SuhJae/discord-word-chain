# This code extracts data from Excel files and saves it to a CSV file.
# No need to run it, since the CSV file is provided upon download.
# It is only for updating the CSV file if the Excel files from the National Institute of the Korean Language
# Standard Korean Dictionary are updated.
# Run this code after running make-csv.py to clean up the CSV file

import pandas as pd

# Read in the input CSV file
df = pd.read_csv('words.csv')

# Clean up the first column
df['어휘'] = df['어휘'].str.replace('-', '').str.replace('^', '').str.replace(r'\([^)]*\)', '').str.strip()

# Remove duplicates from the "어휘" column
df = df.drop_duplicates(subset=['어휘'])

# remove <sub style='font-size:11px;'> and </sub> from the "뜻" column
df['뜻풀이'] = df['뜻풀이'].str.replace(r'<sub style=\'font-size:11px;\'>', '').str.replace(r'</sub>', '')

# Write the cleaned data to a new CSV file
df.to_csv('polished-korean.csv', index=False)
