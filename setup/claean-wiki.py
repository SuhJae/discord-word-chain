import csv

# Open the CSV file
with open('filename.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)

    # Create a list to hold the filtered data
    data = []

    # Loop through each row in the CSV file
    for row in reader:
        # Check if the first column contains a space or only one character
        if ' ' in row[0] or len(row[0]) == 1:
            # Remove the whole row
            continue

        # Otherwise, add the row to the filtered data
        data.append(row)

# Write the filtered data to a new CSV file
with open('polished-wiki.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(data)
