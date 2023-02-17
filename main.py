import nextcord
import redis
from nextcord.ext import commands
from utility import Logger, ConfigReader

logger = Logger()
config = ConfigReader()

r = redis.Redis(host=config.get_value('REDIS', 'host'), port=config.get_value('REDIS', 'port'), db=config.get_value('REDIS', 'db'))

logger.log(f"Connected to Redis {config.get_value('REDIS', 'host') + ':' + config.get_value('REDIS', 'port') + '/' + config.get_value('REDIS', 'db')}")
logger.log('Starting bot...')

intents = nextcord.Intents.default()
intents.members, intents.message_content = True, True

client = commands.Bot()


@client.event
async def on_ready():
    logger.log(f'Logged in as {client.user}')


@client.event
async def on_message(message):
    if message.author.bot:
        return
    else:
        prefix = r.get(message.server.id + ':prefix')
        if message.content.startswith(prefix):
            with r.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch(message.server.id + ':current_letter', message.author.id + ':score')
                        current_letter = pipe.get(message.server.id + ':current_letter')
                        score = int(pipe.get(message.author.id + ':score'))
                        if message.content.startswith(current_letter):
                            # Word is valid, update score and current letter
                            pipe.multi()
                            pipe.incr(message.author.id + ':score', amount=len(message.content))
                            pipe.set(message.server.id + ':current_letter', message.content[-1])
                            pipe.execute()
                            new_score = int(pipe.get(message.author.id + ':score'))
                            new_letter = pipe.get(message.server.id + ':current_letter').decode()
                            await message.channel.send(f'Score: {new_score}, Next letter: {new_letter}')
                        else:
                            # Word is invalid, discard transaction and send error message
                            pipe.discard()
                            await message.channel.send(f"Word must start with letter '{current_letter.decode()}'")
                        break
                    except redis.WatchError:
                        continue
        else:
            message.delete()
            await message.channel.send(f'This does not match the prefix, {prefix.decode()}')


client.run(config.get_value('CREDENTIAL', 'token'))