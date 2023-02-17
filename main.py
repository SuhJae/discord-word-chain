import nextcord
import redis
import random
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
intents.members = True
intents.message_content = True

client = commands.Bot(intents=intents)


@client.event
async def on_ready():
    logger.log(f'Logged in as {client.user}')


@client.slash_command(name = '사전', description = '끝말잇기에서 사용할 수 있는 단어를 검색합니다.')
async def search_words(
    interaction: Interaction,
    word: str = SlashOption(
        name="단어",
        description="검색할 단어를 입력해 주세요.",
    ),
):
    logger.log(f'{interaction.user.name} used /단어검색 command on {interaction.guild.name} server.')

    if interaction.channel.id == int(r.get(f'channel:{interaction.guild.id}')):
        ephemeral = True
    else:
        ephemeral = False

    definition = dictionary.get(word)
    if not definition:
        await interaction.response.send_message(f'"**{word}**" 단어를 찾을 수 없었습니다. 철자를 다시 확인해 주세요. ', ephemeral=True)
        return

    url = ('https://stdict.korean.go.kr/search/searchResult.do?pageSize=10&searchKeyword='+word).replace(' ', '%20')
    description = definition.decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip()

    # sends the autocompleted result
    embed = nextcord.Embed(title="",
    description=f'{description}\n\n__[사전에서 보기]({url})__',
                           color=nextcord.Color.green())
    embed.set_author(name=f"단어 검색 - {word}", icon_url=client.user.avatar.url)

    await interaction.response.send_message(embed=embed ,ephemeral=ephemeral)

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

@client.slash_command(name='설정', description='현재 명령어를 사용한 채널을 끝말잇기 채널로 설정합니다.', default_member_permissions=8)
async def set_channel(
    interaction: Interaction,
):
    # check if bot has permission to send messages and edit messages on the channel
    if not interaction.channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message("끝말잇기 채널로 설정할 수 없습니다. 봇이 메시지를 보낼 권한이 없습니다.", ephemeral=True)
        return
    if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
        await interaction.response.send_message("끝말잇기 채널로 설정할 수 없습니다. 봇이 메시지를 수정할 권한이 없습니다.", ephemeral=True)
        return
    if r.get(f'channel:{interaction.guild.id}'):
        await interaction.response.send_message(f"끝말잇기 채널이 <#{int(r.get('channel:' + str(interaction.guild.id)))}>에서 현재 채널로 변경 되었습니다.", ephemeral=True)
    else:
        await interaction.response.send_message(f'끝말잇기 채널이 {interaction.channel.mention}로 설정되었습니다.', ephemeral=True)

    logger.log(f'{interaction.user.name} used /설정 command on {interaction.guild.name} server.')
    r.set(f'channel:{interaction.guild.id}', interaction.channel.id)
    # select random word
    words = dictionary.keys(f'*기')
    words = [i.decode('utf-8') for i in words]
    word = random.choice(words)

    r.set(f'word:{interaction.guild.id}', word)

    embed = nextcord.Embed(title="끝말잇기 시작!", description=f'끝말잇기를 시작합니다! 첫 단어는 **`{word}`**입니다.', color=nextcord.Color.green())
    await interaction.channel.send(embed=embed)


@client.event
async def on_message(message):
    if message.author.bot:
        return
    if not r.get(f'channel:{message.guild.id}'):
        return
    if message.channel.id == int(r.get(f'channel:{message.guild.id}')):
        word = r.get(f'word:{message.guild.id}').decode('utf-8')
        next_word = message.content

        if len(message.content) < 2:
            embed = nextcord.Embed(title="끝말잇기 오류", description=f'2글자 이상의 단어를 사용해 주세요.', color=nextcord.Color.red())
            await message.channel.send(embed=embed, delete_after=5)
            await message.delete()
            return

        if next_word.startswith(word[-1]):
            if dictionary.get(next_word):
                definition = dictionary.get(next_word)
                description = definition.decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip()
                r.set(f'word:{message.guild.id}', next_word)

                embed = nextcord.Embed(title="", description=f'{description}', color=nextcord.Color.green())
                embed.set_author(name=f"{word} → {next_word}", icon_url=message.author.avatar.url)
                await message.reply(embed=embed, mention_author=False)
            else:
                embed = nextcord.Embed(title="끝말잇기 오류!", description=f'**`{next_word}`**는 사전에 등재되어 있지 않은 단어입니다.\n`/사전`을 이용하여 단어를 찾아보세요.', color=nextcord.Color.red())
                await message.channel.send(embed=embed, delete_after=5)
                await message.delete()
        else:
            embed = nextcord.Embed(title="끝말잇기 오류!", description=f'**`{word[-1]}`**로 시작하는 단어를 입력해 주세요.', color=nextcord.Color.red())
            await message.channel.send(embed=embed, delete_after=5)
            await message.delete()


client.run(config.get_value('CREDENTIAL', 'token'))