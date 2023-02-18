import nextcord
import redis
import hgtk
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


# This function checks for the "두음 법칙" (dubeom beopchik) rule in Korean language, which states that when the initial
# sound of a syllable is either 'ㄴ' or 'ㄹ', and the vowel of the second sound is one of ㅣ, ㅑ, ㅕ, ㅛ, ㅠ, ㅖ, or ㅒ, the
# initial sound of the syllable changes to ㅇ. This function takes a Korean letter as input and decomposes it into its
# constituent parts, checks whether the dubeom beopchik rule applies, and returns the modified initial sound if
# applicable. The three parts of the syllable (initial, vowel, and final sounds) are represented using the "Hangul
# Compatibility Jamo" Unicode characters, and are composed back into a complete syllable using the
# hgtk.letter.compose() function.
def initial_letter(letter):
    sdis = hgtk.letter.decompose(letter)
    if len(sdis) > 1:
        if sdis[0] in ['ㄴ', 'ㄹ'] and sdis[1] in ['ㅣ', 'ㅑ', 'ㅕ', 'ㅛ', 'ㅠ', 'ㅖ', 'ㅒ']:
            sdis_list = list(sdis)
            sdis_list[0] = 'ㅇ'
            sdis = tuple(sdis_list)
        elif sdis[0] == 'ㄹ' and sdis[1] in ['ㅏ', 'ㅗ', 'ㅜ', 'ㅡ']:
            sdis_list = list(sdis)
            sdis_list[0] = 'ㄴ'
            sdis = tuple(sdis_list)
    else:
        sdis += ('', '')  # add missing parts
    return hgtk.letter.compose(*sdis)


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

    r.delete(f'word:{interaction.guild.id}')

    # select random word
    while True:
        word = dictionary.randomkey().decode('utf-8')
        if len(f'*{dictionary.keys(word[-1])}') > 10:
            break

    r.set(f'word:{interaction.guild.id}', word)

    embed = nextcord.Embed(title="끝말잇기 시작!", description=f'끝말잇기를 시작합니다! 첫 단어는 **`{word}`**입니다.', color=nextcord.Color.blue())
    embed.add_field(name='**뜻풀이**', value=dictionary.get(word).decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip())
    await interaction.channel.send(embed=embed)


async def send_error_message(channel, error_description):
    embed = nextcord.Embed(
        title="유효하지 않은 단어",
        description=error_description,
        color=nextcord.Color.red()
    )
    embed.set_footer(text='게임 초기화를 원하시면 /재시작 명령어를 사용해 주세요.')
    await channel.send(embed=embed, delete_after=5)


@client.event
async def on_message(message):
    if message.author.bot or not r.get(f'channel:{message.guild.id}'):
        return

    channel_id = int(r.get(f'channel:{message.guild.id}'))
    if message.channel.id != channel_id:
        return

    word = r.get(f'word:{message.guild.id}').decode('utf-8')
    next_word = message.content

    if len(next_word) < 2:
        await send_error_message(message.channel, '2글자 이상의 단어를 사용해 주세요.')
        await message.delete()
        return

    dubem = initial_letter(word[-1])
    is_dubem = dubem != word[-1]
    is_valid_word = dictionary.get(next_word)

    if not next_word.startswith(word[-1]) and not (is_dubem and next_word.startswith(dubem)):
        error = word[-1] if not is_dubem else f'{word[-1]}({dubem})'
        await send_error_message(message.channel, f'**{error}**로 시작하는 단어를 입력해 주세요.')
        await message.delete()
        return

    if not is_valid_word:
        await send_error_message(message.channel, f'**{next_word}**는 사전에 등재되어 있지 않은 단어입니다.\n`/사전`을 이용하여 단어를 찾아보세요.')
        await message.delete()
        return

    used_key = f"used:{message.guild.id}:{next_word}"
    if r.exists(used_key):
        used_message_id = r.get(used_key)
        if used_message_id:
            used_message = await message.channel.fetch_message(int(used_message_id))
            await send_error_message(message.channel, f'**{next_word}**는 __[여기서]({used_message.jump_url})__ 이미 사용된 단어입니다.')
        else:
            await send_error_message(message.channel, f'**{next_word}**는 이미 사용된 단어입니다.')
        await message.delete()
        return
    r.set(used_key, message.id)

    definition = is_valid_word.decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace(
        '[', '`[').replace(']', ']`').strip()
    r.set(f'word:{message.guild.id}', next_word)

    if is_dubem:
        name = f"{word} → {next_word}"
    else:
        name = f"{word}({dubem}) → {next_word}"
    n_bubem = initial_letter(next_word[-1])
    if n_bubem != next_word[-1]:
        name += f'({n_bubem})'

    embed = nextcord.Embed(
        title="",
        description=f'{definition}',
        color=nextcord.Color.green()
    )
    embed.set_author(name=name, icon_url=message.author.avatar.url)
    await message.reply(embed=embed, mention_author=False)


@client.slash_command(name='재시작', description='끝말잇기를 처음부터 다시 시작합니다.')
async def restart_game(interaction: Interaction):
    logger.log(f'{interaction.user.name} used /재시작 command on {interaction.guild.name} server.')
    server_id = interaction.guild.id
    await interaction.response.send_message(f'끝말잇기를 초기화 합니다.', ephemeral=True)

    # clear used word keys
    used_keys = r.keys(f'used:{server_id}:*')
    for key in used_keys:
        r.delete(key)

    # set new word
    r.delete(f'word:{server_id}')
    while True:
        word = dictionary.randomkey().decode('utf-8')
        if len(f'*{dictionary.keys(word[-1])}') > 10:
            break
    r.set(f'word:{server_id}', word)

    embed = nextcord.Embed(title="끝말잇기 시작!", description=f'끝말잇기를 다시 시작합니다! 첫 단어는 **{word}**입니다.',
                           color=nextcord.Color.blue())
    embed.add_field(name='**뜻풀이**', value=dictionary.get(word).decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip())
    embed.set_footer(text=f"{interaction.user.display_name}님의 요청으로 게임이 재시작 되었습니다.")
    start = await interaction.channel.send(embed=embed)
    r.set(f'used:{server_id}:{word}', start.id)


# when joining new server
@client.event
async def on_guild_join(guild):
    logger.log(f'Joined {guild.name}({guild.id})')


# when leaving server
@client.event
async def on_guild_remove(guild):
    logger.log(f'Left {guild.name}({guild.id})')


client.run(config.get_value('CREDENTIAL', 'token'))