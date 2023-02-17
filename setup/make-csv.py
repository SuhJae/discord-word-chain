# This code extracts data from Excel files and saves it to a CSV file.
# No need to run it, since the CSV file is provided upon download.
# It is only for updating the CSV file if the Excel files from the National Institute of the Korean Language
# Standard Korean Dictionary are updated.
# After, run cleanup.py to clean up the CSV file

import pandas as pd
df = pd.DataFrame()

for i in range(1, 16):
    filename = f'original/words-{i}.xls'
    data = pd.read_excel(filename, usecols=['어휘', '뜻풀이', '구성 단위'])

    # Replace new lines in the '뜻풀이' column with a string that represents a new line
    data['뜻풀이'] = data['뜻풀이'].str.replace('\n', '\\n')

    df = pd.concat([df, data], ignore_index=True)

# Save the extracted data to a CSV file
df.to_csv('words.csv', index=False)
