import discord
from discord.ext import commands
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
import matplotlib.pyplot as plt
import io
from PIL import Image, ImageDraw, ImageFont

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(commands.when_mentioned_or('!'), intents=intents)


@bot.event
async def on_ready():
    print(f"current login ---> {bot.user}")


@bot.command()
async def search(ctx, *arg):
    r = players.get_players()
    search = " ".join(arg)
    if not arg:
        await ctx.send("Type some player name. . .")
        return

    await ctx.send("Fetching Data. . .")
    try:
        playerID = [player for player in r if player['full_name']
                    == search][0]['id']
        career = playercareerstats.PlayerCareerStats(player_id=playerID)
    except:
        await ctx.send("Spelled wrong player name, try again")
        return

    p = pd.DataFrame({
        'GP': career.get_data_frames()[1]['GP'],
        'GS': career.get_data_frames()[1]['GS'],
        'PTS': career.get_data_frames()[1]['PTS']
    })
    p = p.to_string(index=False)
    p = '```' + p + '```'
    await ctx.send(p)
    return


@bot.command()
async def games(ctx):
    """
    將當天賽程排版成簡單的一張圖片，再輸出到 Discord
    """
    games_data = scoreboard.ScoreBoard().games.get_dict()
    if not games_data:
        await ctx.send("今日沒有比賽喔")
        return

    # 先把賽程文字整理好
    game_texts = []
    for game in games_data:
        # 注意：因為NBA官方提供的時間是 UTC，你可依需求轉當地時區
        text_line = f"{game['gameTimeUTC']} | {game['homeTeam']['teamName']} vs {game['awayTeam']['teamName']}"
        game_texts.append(text_line)

    # 用 Pillow 來生成一張簡單的圖片
    # 設定一些圖片參數
    bg_color = (255, 255, 255)
    font_color = (0, 0, 0)
    padding = 20
    line_spacing = 40

    # 設定字體，如果本地沒有安裝，可換成其他系統字體
    # Windows 可使用 'arial.ttf'，Mac 或 Linux 可換成其他可用字體檔案
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        # 如果沒有 arial.ttf，就使用 PIL 內建字體 (樣式有限)
        font = ImageFont.load_default()

    # 計算圖片大小
    width = 800
    height = padding * 2 + line_spacing * len(game_texts)

    # 建立圖片
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 逐行將 game_texts 寫進圖片
    y_text = padding
    for line in game_texts:
        draw.text((padding, y_text), line, font=font, fill=font_color)
        y_text += line_spacing

    # 存到記憶體再上傳
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    file = discord.File(fp=img_bytes, filename="games_today.png")

    # 送出圖片檔案
    await ctx.send(file=file)


@bot.command()
async def team(ctx, *arg):
    """
    先用原本的 DataFrame 輸出，
    再另外做一張 最近五場比賽 PTS 的折線圖
    """
    team_name = " ".join(arg)
    if not arg:
        await ctx.send("Type some Team. . .")
        return
    await ctx.send("Fetching Data. . .")

    try:
        teamID = teams.find_teams_by_full_name(team_name)
        findGame = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=teamID[0]['id'])
    except:
        await ctx.send("Spelled wrong team name, try again")
        return

    # 取最近五場比賽
    all_games = findGame.get_data_frames()[0]
    last_five = all_games.head(5)
    g = pd.DataFrame({
        'GAME_DATE': last_five['GAME_DATE'],
        'MATCHUP': last_five['MATCHUP'],
        'WL': last_five['WL'],
        'PTS': last_five['PTS'],
        'FGM': last_five['FGM'],
        'FGA': last_five['FGA'],
        'FG3M': last_five['FG3M'],
        'FG3A': last_five['FG3A'],
        'FTM': last_five['FTM'],
        'FTA': last_five['FTA'],
        'OREB': last_five['OREB'],
        'DREB': last_five['DREB'],
        "AST": last_five["AST"],
        'STL': last_five["STL"],
        "BLK": last_five["BLK"],
        "TOV": last_five["TOV"],
        "PF": last_five["PF"]
    })
    g_str = g.to_string(index=False)
    g_str = '```' + g_str + '```'
    await ctx.send(g_str)

    # 產生簡單的折線圖 (以 PTS 為例)
    plt.figure(figsize=(6, 4), dpi=100)
    # x 軸用日期字串
    x_values = range(len(last_five))
    y_values = last_five['PTS']

    plt.plot(x_values, y_values, marker='o',
             linestyle='-', color='blue', label='PTS')
    plt.xticks(x_values, last_five['GAME_DATE'], rotation=45)
    plt.title(f"Last 5 Games PTS - {team_name}")
    plt.xlabel("Game Date")
    plt.ylabel("Points")
    plt.legend()
    plt.tight_layout()

    # 存到記憶體再上傳
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    file = discord.File(buf, filename="last5games.png")
    await ctx.send(file=file)

bot.run("TOKEN")
