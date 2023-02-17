


import pandas as pd

# Create an empty DataFrame to store the extracted data
df = pd.DataFrame()

# Loop through the Excel files and extract the columns of interest
for i in range(1, 16):
    filename = f'original/words-{i}.xls'
    data = pd.read_excel(filename, usecols=['어휘', '뜻풀이', '구성 단위'])

    # Replace new lines in the '뜻풀이' column with a string that represents a new line
    data['뜻풀이'] = data['뜻풀이'].str.replace('\n', '\\n')

    df = pd.concat([df, data], ignore_index=True)

# Save the extracted data to a CSV file
df.to_csv('words.csv', index=False)
