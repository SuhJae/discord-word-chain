import configparser
import datetime

class Logger:
    def log(self, message):
        current_time = datetime.datetime.now().strftime('%H:%M:%S')
        print(f'\033[92m[{current_time}]\033[0m {message}')

class ConfigReader:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

    def get_value(self, section, key):
        return self.config.get(section, key)