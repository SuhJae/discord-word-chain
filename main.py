import nextcord
import redis
from nextcord import Interaction, SlashOption
from nextcord.ext import commands
from utility import Logger, ConfigReader

logger = Logger()
config = ConfigReader()

r = redis.Redis(host=config.get_value('REDIS', 'host'), port=config.get_value('REDIS', 'port'), db=config.get_value('REDIS', 'db'))
dictionary = redis.Redis(host=config.get_value('DICTIONARY', 'host'), port=config.get_value('DICTIONARY', 'port'), db=config.get_value('DICTIONARY', 'db'))

logger.log(f"Connected to Redis {config.get_value('REDIS', 'host') + ':' + config.get_value('REDIS', 'port') + '/' + config.get_value('REDIS', 'db')}")
logger.log('Starting bot...')

intents = nextcord.Intents.default()
intents.members, intents.message_content = True, True

client = commands.Bot()


@client.event
async def on_ready():
    logger.log(f'Logged in as {client.user}')


@client.slash_command(name = '단어검색', description = '끝말잇기에서 사용할 수 있는 단어를 검색합니다.')
async def search_words(
    interaction: Interaction,
    word: str = SlashOption(
        name="단어",
        description="검색할 단어를 입력해 주세요.",
    ),
):
    definition = dictionary.get(word)
    if not definition:
        await interaction.response.send_message("단어를 찾을 수 없습니다.", ephemeral=True)
        return

    url = f'https://stdict.korean.go.kr/search/searchResult.do?pageSize=10&searchKeyword={word}'
    description = definition.decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').strip()

    # sends the autocompleted result
    embed = nextcord.Embed(title=f"단어 검색 - {word}",
    description=f'{description}\n\n__[사전에서 보기]({url})__',
                           color=nextcord.Color.green())

    await interaction.response.send_message(embed=embed)

@search_words.on_autocomplete("word")
async def preview(interaction: Interaction, word: str):
    if not word:
        # get 25 random keys using pipeline
        with dictionary.pipeline() as pipe:
            keywords = []
            for i in range(25):
                pipe.randomkey()
            for key in pipe.execute():
                keywords.append(key.decode('utf-8').replace('W:', ''))
            keywords.sort()
            await interaction.response.send_autocomplete(keywords)

    else:
        matches = dictionary.keys(word + "*")
        matches = matches[:25]
        matches = [match.decode('utf-8') for match in matches]
        await interaction.response.send_autocomplete(matches)

client.run(config.get_value('CREDENTIAL', 'token'))