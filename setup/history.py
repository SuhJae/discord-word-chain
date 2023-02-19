import pandas as pd

# Read in the CSV file
df = pd.read_csv('original/historic.csv')

# Define a function to create the "meaning" column
def create_meaning(row):
    term_lk = row['term_lk']
    term_desc = row['term_desc']
    return f'「역사 용어」 [{term_lk}] {term_desc}'

# Apply the create_meaning function to each row of the dataframe
df['meaning'] = df.apply(create_meaning, axis=1)

# Select only the "term_name" and "meaning" columns
df = df[['term_name', 'meaning']]

# Write the data to a CSV file
df.to_csv('historic.csv', index=False)
