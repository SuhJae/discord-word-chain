import nextcord
from utility import ConfigReader

config = ConfigReader()

class SimpleEmbed:
    def error(self, message):
        return nextcord.Embed(title='', description=":x: " + message, colour=0x2B2D31)

    def success(self, message):
        return nextcord.Embed(title='', description=":white_check_mark: " + message, colour=0x2B2D31)

    def info(self, message):
        return nextcord.Embed(title='', description=config.get_value(":information_source: " + message, colour=0x2B2D31))

