# Run this script to upload the words to Redis
# Make sure to edit the config.ini file IN THE SETUP DIRECTORY to match your Redis server's settings

from utility import Logger, ConfigReader
from concurrent.futures import ThreadPoolExecutor
import redis
import csv

logger = Logger()
config = ConfigReader()

r = redis.Redis(host=config.get_value('REDIS', 'host'), port=config.get_value('REDIS', 'port'), db=config.get_value('REDIS', 'db'))
try:
    r.ping()
    logger.log(f"Connected to Redis {config.get_value('REDIS', 'host') + ':' + config.get_value('REDIS', 'port') + '/' + config.get_value('REDIS', 'db')}")
except redis.exceptions.ConnectionError:
    logger.log('Failed to connect to Redis')
    exit(1)

# Define a function for uploading words and their meanings to Redis

def upload_words(words, meanings):
    # Use a pipeline to batch upload the words
    pipeline = r.pipeline()
    for word, meaning in zip(words, meanings):
        if len(words) > 2:
            pipeline.set(word, meaning)
    pipeline.execute()


print('Uploading words...')

# Read the words from the CSV file
with open('polished-korean.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    words = []
    definitions = []
    for row in reader:
        words.append(row[0])
        definitions.append(row[2])
        # Upload the words in batches of 1000
        if len(words) == 1000:
            with ThreadPoolExecutor() as executor:
                executor.submit(upload_words, words, definitions)
            words = []
            definitions = []
    # Upload any remaining words
    if words:
        with ThreadPoolExecutor() as executor:
            executor.submit(upload_words, words, definitions)

print('Done')