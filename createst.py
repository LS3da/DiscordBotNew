import discord
import os
import random
import markovify
from discord.ext import commands
from janome.tokenizer import Tokenizer

# コマンド機能を使うBotを定義
bot = commands.Bot(
    command_prefix='!',
    intents=discord.Intents.all()
)

# ----------------------------------------------------
# 1. 学習済みモデルの準備 (Bot起動時に一度だけ実行)
# ----------------------------------------------------
# Janomeの準備
t = Tokenizer()

# トークナイザー関数を定義
def japanese_tokenizer(text):
    return t.tokenize(text, wakati=True)

try:
    with open("text.txt", encoding="utf-8") as f:
        text = f.read()

    # 元のテキストを改行で文ごとにリスト化する
    lines = text.split('\n')

    # それぞれの文を分かち書きし、スペースで連結したリストを作成する
    tokenized_sentences = []
    for line in lines:
        if line: # 空行は学習データに含めない
            tokenized_sentences.append(" ".join(japanese_tokenizer(line)))

    # 分かち書き済みの文のリストを、再び改行で連結して一つのテキストに戻す
    processed_text = "\n".join(tokenized_sentences)

    # markovifyの厳格な内部チェックを緩和するため `well_formed=False` を追加
    text_model = markovify.Text(processed_text, state_size=2, well_formed=False)

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
    print(f'Login OK: {bot.user} (ID: {bot.user.id})')

# !marukofuコマンド（通常の長さの文章を生成）
@bot.command()
async def marukofu(ctx):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return

    # 通常の文章を生成（最大140文字）
    sentence = text_model.make_sentence(tries=100, max_chars=140)
    
    if sentence:
        await ctx.send(sentence.replace(" ", ""))
    else:
        await ctx.send("ごめんなさい、学習データに基づいて文章をうまく生成できませんでした。")


# ======================= ここからが追加したコマンドです =======================

# !marukofushortコマンド（短い文章を生成）
@bot.command()
async def marukofushort(ctx):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return

    # 短い文章を生成（最大70文字）
    # 💡 make_sentence -> make_short_sentence に変更
    sentence = text_model.make_short_sentence(tries=100, max_chars=70)
    
    if sentence:
        await ctx.send(sentence.replace(" ", ""))
    else:
        await ctx.send("ごめんなさい、学習データに基づいて短い文章をうまく生成できませんでした。")

# ======================= ここまでが追加したコマンドです =======================


# !omikujiコマンド
@bot.command()
async def omikuji(ctx):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    results = ["大吉 🥳", "中吉 😊", "小吉 🙂", "吉 😉", "末吉 😐", "凶 😟", "大凶 😭"]
    fortune = random.choice(results)
    await ctx.send(f'{ctx.author.display_name} さんの今日の運勢は... **{fortune}** です！')


# !createstsaymessageコマンド
@bot.command()
async def createstsaymessage(ctx, *, message: str):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    await ctx.send(message)

# Botの起動
bot.run(os.environ['DISCORD_BOT_TOKEN'])
