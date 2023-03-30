import asyncio

import hgtk
import nextcord
import redis
from hgtk.exception import NotHangulException
from nextcord import Interaction, SlashOption
from nextcord.ext import commands

from formatting import SimpleEmbed
from utility import Logger, ConfigReader

logger, config, SE = Logger(), ConfigReader(), SimpleEmbed()
r = redis.Redis(host=config.get_value('REDIS', 'host'), port=config.get_value('REDIS', 'port'),
                db=config.get_value('REDIS', 'db'))
dictionary = redis.Redis(host=config.get_value('DICTIONARY', 'host'), port=config.get_value('DICTIONARY', 'port'),
                         db=config.get_value('DICTIONARY', 'db'))

logger.log(
    f"Connected to Redis {config.get_value('REDIS', 'host') + ':' + config.get_value('REDIS', 'port') + '/' + config.get_value('REDIS', 'db')}")
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
    try:
        return hgtk.letter.compose(*sdis)
    except NotHangulException:
        return letter.lower()


@client.event
async def on_ready():
    logger.log(f'Logged in as {client.user}')


@client.slash_command(name='사전', description='끝말잇기에서 사용할 수 있는 단어를 검색합니다.')
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
        await interaction.response.send_message(embed=SE.error(f'"**{word}**" 단어를 찾을 수 없었습니다. 철자를 다시 확인해 주세요.'), ephemeral=True)
        return

    if definition.decode('utf-8').startswith('「어인정」'):
        url = ('https://kkukowiki.kr/w/' + word).replace(' ', '%20')
    elif definition.decode('utf-8').startswith('「역사 용어」'):
        url = (
                    'https://db.history.go.kr/search/searchResult.do?sort=levelId&dir=ASC&start=-1&limit=20&page=1&pre_page=1&itemIds=&codeIds=&synonym=off&chinessChar=on&searchTermImages=' + word + '&searchKeywordType=BI&searchKeywordMethod=EQ&searchKeyword=가&searchKeywordConjunction=AND').replace(
            ' ', '%20')
    else:
        url = ('https://stdict.korean.go.kr/search/searchResult.do?pageSize=10&searchKeyword=' + word).replace(' ','%20')
    description = definition.decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip().replace('``', '` `')

    # sends the autocompleted result
    embed = nextcord.Embed(title="",
                           description=f'{description}\n\n__[사전에서 보기]({url})__',
                           color=nextcord.Color.green())
    embed.set_author(name=f"단어 검색 - {word}", icon_url=client.user.avatar.url)

    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


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
        await interaction.response.send_message(embed=SE.error("끝말잇기 채널로 설정할 수 없습니다. 봇이 메시지를 보낼 권한이 없습니다."), ephemeral=True)
        return
    if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
        await interaction.response.send_message(embed=SE.error("끝말잇기 채널로 설정할 수 없습니다. 봇이 메시지를 수정할 권한이 없습니다."), ephemeral=True)
        return
    if r.get(f'channel:{interaction.guild.id}'):
        await interaction.response.send_message(embed=SE.success(f"끝말잇기 채널이 <#{int(r.get('channel:' + str(interaction.guild.id)))}>에서 현재 채널로 변경 되었습니다."), ephemeral=True)
    else:
        await interaction.response.send_message(embed=SE.success(f'끝말잇기 채널이 {interaction.channel.mention}로 설정되었습니다.'), ephemeral=True)

    logger.log(f'{interaction.user.name} used /설정 command on {interaction.guild.name} server.')
    r.set(f'channel:{interaction.guild.id}', interaction.channel.id)

    r.delete(f'word:{interaction.guild.id}')

    # select random word
    while True:
        word = dictionary.randomkey().decode('utf-8')
        if len(f'*{dictionary.keys(word[-1])}') > 10:
            break

    r.set(f'word:{interaction.guild.id}', word)

    embed = nextcord.Embed(title="끝말잇기 시작!", description=f'끝말잇기를 시작합니다! 첫 단어는 **`{word}`**입니다.',
                           color=nextcord.Color.blue())
    embed.add_field(name='**뜻풀이**',
                    value=dictionary.get(word).decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip().replace('``', '` `'))
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
    if message.author.id == 814053998201274388 and message.content == '!공지':
        msg = await message.reply(f'{len(client.guilds)}개의 서버에 공지를 전송을 시작할까요? 만일 그렇다면 10 초 안에 `!확인`를 한 번 더 입력해 주세요.',
                                  mention_author=False)
        try:
            confirmation = await client.wait_for('message', check=lambda
                m: m.author.id == 814053998201274388 and m.content == '!확인', timeout=10)
            if confirmation:
                await msg.channel.send(content='30 초 안에 공지할 내용을 입력해 주세요.')
                try:
                    msg = await client.wait_for('message', check=lambda m: m.author.id == 814053998201274388,
                                                timeout=30)
                    notice = msg.content

                    embed = nextcord.Embed(title="공지", description=notice, color=nextcord.Color.purple())
                    embed.set_footer(text='이 메세지는 끝말잇기 봇 개발자로부터 전송되었습니다.')

                    msg = await msg.channel.send(content='공지를 전송합니다...')

                    # Key: channel:<guild id>
                    # Vale: channel id

                    channels = r.keys('channel:*')
                    for channel_key in channels:
                        guild_id = int(channel_key.decode('utf-8').split(':')[1])

                        try:
                            guild = client.get_guild(guild_id)
                            channel_id = int(r.get(channel_key))
                            channel = guild.get_channel(channel_id)
                        except:
                            logger.log(f'Failed to get channel from {guild_id} guild.')
                        try:
                            await channel.send(embed=embed)
                            logger.log(f'Sent notice to {guild_id} guild.')
                        except:
                            logger.log(f'Failed to send notice to {guild_id} guild.')

                    await msg.channel.send(content=f'{len(client.guilds)}개의 서버에 공지를 전송했습니다.')
                except asyncio.TimeoutError:
                    await msg.channel.send(content='시간이 초과되어 취소되었습니다.')
                    return
        except asyncio.TimeoutError:
            await msg.edit(content='시간이 초과되어 취소되었습니다.')
            return

    if message.author.bot or not r.get(f'channel:{message.guild.id}'):
        return

    if message.content.startswith('> '):
        return

    channel_id = int(r.get(f'channel:{message.guild.id}'))
    if message.channel.id != channel_id:
        return

    word = r.get(f'word:{message.guild.id}')
    if word is None:
        return
    word = word.decode('utf-8')

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
            await send_error_message(message.channel,
                                     f'**{next_word}**는 __[여기서]({used_message.jump_url})__ 이미 사용된 단어입니다.')
        else:
            await send_error_message(message.channel, f'**{next_word}**는 이미 사용된 단어입니다.')
        await message.delete()
        return
    r.set(used_key, message.id)

    definition = is_valid_word.decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip().replace('``', '` `')
    r.set(f'word:{message.guild.id}', next_word)

    if not is_dubem:
        name = f"{word} → {next_word}"
    else:
        name = f"{word}({dubem}) → {next_word}"
    n_bubem = initial_letter(next_word[-1])
    if n_bubem != next_word[-1]:
        name += f'({n_bubem})'

    await message.delete()

    embed = nextcord.Embed(
        title=name,
        description=f'{definition}',
        color=0x2B2D31
    )

    if message.author.avatar.url != None:
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
    else:
        embed.set_author(name=message.author.display_name, icon_url=client.user.avatar.url)
    msg = await message.channel.send(embed=embed)
    r.set(used_key, msg.id)

    # check for game over
    keys = dictionary.keys(f'{next_word[-1]}*')
    keys = [key.decode('utf-8') for key in keys]

    with r.pipeline() as pipe:
        for key in keys:
            pipe.exists(f'used:{key}')
        results = pipe.execute()

    unused_keys = [key for key, result in zip(keys, results) if not result]

    if len(unused_keys) == 0:
        await game_over(message, next_word)
        await reset(message)
        return
    elif len(unused_keys) == 1 and len(keys[0]) == 1:
        await game_over(message, next_word)
        await reset(message)
        return


async def reset(message):
    # clear used word keys
    used_keys = r.keys(f'used:{message.guild.id}:*')
    for key in used_keys:
        r.delete(key)

    # set new word
    r.delete(f'word:{message.guild.id}')
    while True:
        word = dictionary.randomkey().decode('utf-8')
        if len(f'*{dictionary.keys(word[-1])}') > 10:
            break
    r.set(f'word:{message.guild.id}', word)

    embed = nextcord.Embed(title="끝말잇기 시작!", description=f'끝말잇기를 다시 시작합니다! 첫 단어는 **{word}**입니다.',
                           color=nextcord.Color.blue())
    embed.add_field(name='**뜻풀이**',
                    value=dictionary.get(word).decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip().replace('``', '` `'))
    embed.set_footer(text=f"{message.author.display_name}님의 이을 수 없는 단어로 게임이 재시작 되었습니다.")
    start = await message.channel.send(embed=embed)
    r.set(f'used:{message.guild.id}', start.id)


async def game_over(message, next_word):
    embed = nextcord.Embed(
        title="게임오버!",
        description=f'{message.author.display_name}님이 사용하신 **{next_word}**에 이을 단어가 더 없습니다!\n게임이 다시 시작됩니다!',
        color=nextcord.Color.red()
    )
    combo = len(r.keys(f'used:{message.guild.id}:*'))
    embed.set_footer(text=f'콤보: {combo}단어')
    await message.channel.send(embed=embed)
    r.delete(f'word:{message.guild.id}')


@client.slash_command(name='재시작', description='끝말잇기를 처음부터 다시 시작합니다.')
async def restart_game(interaction: Interaction):
    logger.log(f'{interaction.user.name} used /재시작 command on {interaction.guild.name} server.')
    server_id = interaction.guild.id

    # thinking
    await interaction.response.defer(ephemeral=False, with_message=True)

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
    embed.add_field(name='**뜻풀이**',
                    value=dictionary.get(word).decode('utf-8').replace('\\n', '\n').replace('「', '`「').replace('」', '」`').replace('[', '`[').replace(']', ']`').strip().replace('``', '` `'))
    embed.set_footer(text=f"{interaction.user.display_name}님의 요청으로 게임이 재시작 되었습니다.")
    start = await interaction.followup.send(embed=embed, ephemeral=False)
    r.set(f'used:{server_id}:{word}', start.id)


@client.slash_command(name='콤보', description='서버의 현재 콤보를 확인합니다.')
async def get_combo(interaction: Interaction):
    logger.log(f'{interaction.user.name} used /콤보 command on {interaction.guild.name} server.')
    server_id = interaction.guild.id
    used_keys = r.keys(f'used:{server_id}:*')

    combo = len(used_keys)
    embed = nextcord.Embed(title="서버 콤보", description=f'서버의 현재 끝말잇기 콤보는 **{combo}**입니다.',
                           color=nextcord.Color.blue())

    channel = r.get(f'channel:{server_id}')
    if channel == None:
        await interaction.response.send_message(embed=SE.error('아직 서버에 채널이 설정되지 않았습니다.'), ephemeral=True)
    else:
        channel = int(channel)
        if interaction.channel.id == channel:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed)


# when joining new server
@client.event
async def on_guild_join(guild):
    logger.log(f'Joined {guild.name}({guild.id})')


# when leaving server
@client.event
async def on_guild_remove(guild):
    logger.log(f'Left {guild.name}({guild.id})')


client.run(config.get_value('CREDENTIAL', 'token'))
