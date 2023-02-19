import csv

# Open the CSV file
with open('wiki-import.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)

    # Create a list to hold the filtered and modified data
    data = []

    # Loop through each row in the CSV file
    for row in reader:
        # Check if the first column contains a space or only one character
        if ' ' in row[0] or len(row[0]) == 1:
            # Remove the whole row
            continue

        # Otherwise, modify the row and add it to the filtered data
        row.append(" 「어인정」 비디오 게임")
        data.append(row)

# Write the filtered and modified data to a new CSV file
with open('polished wiki.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(data)
