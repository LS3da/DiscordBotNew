import discord
import os
import random
import markovify # 👈 markovify ライブラリをインポート
from discord.ext import commands

# コマンド機能を使うBotを定義
bot = commands.Bot(
    command_prefix='!',
    intents=discord.Intents.all()
)

# ----------------------------------------------------
# 1. 学習済みモデルの準備 (Bot起動時に一度だけ実行)
# ----------------------------------------------------
try:
    with open("text.txt", encoding="utf-8") as f:
        text = f.read()

    # マルコフモデルを生成
    # state_size=2 は「2単語前までの情報」を使って次の単語を予測
    text_model = markovify.Text(text, state_size=2)
    print("マルコフモデルの構築に成功しました。")
    MODEL_READY = True
except FileNotFoundError:
    print("学習データ 'text.txt' が見つかりません。マルコフコマンドは使用できません。")
    MODEL_READY = False
except Exception as e:
    print(f"マルコフモデルの構築中にエラーが発生しました: {e}")
    MODEL_READY = False
# ----------------------------------------------------


@bot.event
async def on_ready():
    # Botが正常にログインしたことを確認
    print(f'Login OK: {bot.user} (ID: {bot.user.id})')
    # 接続確認用のステータス設定などをここに追加できます

# !marukofuコマンド：マルコフ連鎖で文章を生成 (新しい機能)
@bot.command()
async def marukofu(ctx):
    await ctx.message.delete()
    
    # モデルが正常に構築されていない場合はエラーメッセージを送信して終了
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return

    # 新しい文章を生成（最大100文字、100回試行）
    sentence = text_model.make_sentence(tries=100, max_chars=100)
    
    if sentence:
        await ctx.send(sentence)
    else:
        await ctx.send("ごめんなさい、学習データに基づいて文章をうまく生成できませんでした。")


# !omikujiコマンド：おみくじを引く
@bot.command()
async def omikuji(ctx):
    await ctx.message.delete()
    # おみくじの結果のリストを定義
    results = [
        "大吉 🥳",
        "中吉 😊",
        "小吉 🙂",
        "吉 😉",
        "末吉 😐",
        "凶 😟",
        "大凶 😭"
    ]
    
    # リストから結果をランダムに一つ選択
    fortune = random.choice(results)
    
    # 結果をDiscordに送信
    await ctx.send(f'{ctx.author.display_name} さんの今日の運勢は... **{fortune}** です！')


# !createstsaymessageコマンド：ユーザーが入力した内容をそのままBotが送信
@bot.command()
async def createstsaymessage(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

# Botの起動
bot.run(os.environ['DISCORD_BOT_TOKEN'])
