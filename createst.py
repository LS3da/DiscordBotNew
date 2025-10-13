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

    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ ここが最後の修正箇所です ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    
    # 以前のコード：
    # processed_text = "\n".join(tokenized_sentences)
    # text_model = markovify.Text(processed_text, state_size=2, well_formed=False)

    # 💡 新しいコード：
    # 巨大な文字列ではなく、文章の「リスト」を直接渡す。
    # これにより、文の始まりが偏る問題を完全に解決し、真のランダム性を実現する。
    text_model = markovify.Text(tokenized_sentences, state_size=2, well_formed=False)

    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ ここまでが最後の修正箇所です ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

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

# !marukofuコマンド
@bot.command()
async def marukofu(ctx):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return

    sentence = text_model.make_sentence(tries=100, max_chars=140)
    
    if sentence:
        await ctx.send(sentence.replace(" ", ""))
    else:
        await ctx.send("ごめんなさい、学習データに基づいて文章をうまく生成できませんでした。")


# !marukofushortコマンド
@bot.command()
async def marukofushort(ctx):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return

    long_sentence = text_model.make_sentence(tries=100, max_chars=140)
    
    sentence = None
    if long_sentence:
        clean_sentence = long_sentence.replace(" ", "")
        kuten_index = clean_sentence.find("。")
        if kuten_index != -1:
            sentence = clean_sentence[:kuten_index + 1]
        else:
            touten_index = clean_sentence.find("、")
            if touten_index != -1:
                sentence = clean_sentence[:touten_index + 1]
            else:
                sentence = clean_sentence
    
    if sentence:
        await ctx.send(sentence)
    else:
        await ctx.send("ごめんなさい、学習データに基づいて短い文章をうまく生成できませんでした。")


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
