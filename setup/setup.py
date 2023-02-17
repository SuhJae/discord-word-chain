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

r.delete("words")

logger.log('Uploading words to Redis... This may take a while.')


# Define the function to upload words to Redis
def upload_words(words):
    # Use a pipeline to batch upload the words
    pipeline = r.pipeline()
    for word in words:
        pipeline.zadd('words', {word: 0})
    pipeline.execute()


# Read the words from the CSV file
with open('korean words.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    words = []
    for row in reader:
        words.append(row[0])
        # Upload the words in batches of 1000
        if len(words) == 1000:
            with ThreadPoolExecutor() as executor:
                executor.submit(upload_words, words)
            words = []
    # Upload any remaining words
    if words:
        with ThreadPoolExecutor() as executor:
            executor.submit(upload_words, words)


logger.log('Done!')


