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

    lines = text.split('\n')
    tokenized_sentences = []
    for line in lines:
        if line:
            tokenized_sentences.append(" ".join(japanese_tokenizer(line)))
    processed_text = "\n".join(tokenized_sentences)
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

    sentence = text_model.make_sentence(tries=100, max_chars=140)
    
    if sentence:
        await ctx.send(sentence.replace(" ", ""))
    else:
        await ctx.send("ごめんなさい、学習データに基づいて文章をうまく生成できませんでした。")


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

    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ ここからロジックを大幅に変更 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼

    # 💡 1. まずは普通の文章を生成してみる（文字数制限は緩め）
    long_sentence = text_model.make_sentence(tries=100, max_chars=140)
    
    sentence = None # 最終的に送信する文章を入れる変数
    if long_sentence:
        # 💡 2. 生成した文章を「。」や「、」で短く加工する
        clean_sentence = long_sentence.replace(" ", "") # 先にスペースを削除
        
        # 最初の「。」を探す
        kuten_index = clean_sentence.find("。")
        if kuten_index != -1:
            # 「。」が見つかれば、そこまでを文章とする
            sentence = clean_sentence[:kuten_index + 1]
        else:
            # 「。」がなければ、最初の「、」を探す
            touten_index = clean_sentence.find("、")
            if touten_index != -1:
                # 「、」が見つかれば、そこまでを文章とする
                sentence = clean_sentence[:touten_index + 1]
            else:
                # 「。」も「、」もなければ、そのまま使う
                sentence = clean_sentence

    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ ここまでロジックを大幅に変更 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    
    if sentence:
        await ctx.send(sentence) # すでにスペースは削除済みなのでそのまま送信
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
