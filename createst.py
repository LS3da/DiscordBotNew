import discord
import os
import random
import markovify
from discord.ext import commands
from janome.tokenizer import Tokenizer
import google.generativeai as genai

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# (省略... Geminiとマルコフの準備部分は変更なし)
# ...
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_READY = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-flash-latest') # ◀️ あなたが発見した最新モデル名
        print("Geminiモデルの準備に成功しました。")
        GEMINI_READY = True
    except Exception as e:
        print(f"Geminiモデルの準備中にエラーが発生しました: {e}")
else:
    print("環境変数 'GEMINI_API_KEY' が見つかりません。Geminiコマンドは使用できません。")

t = Tokenizer()
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
    text_model = markovify.Text(tokenized_sentences, state_size=2, well_formed=False)
    print("マルコフモデルの構築に成功しました。")
    MODEL_READY = True
except Exception as e:
    print(f"マルコフモデルの構築中にエラーが発生しました: {e}")
    MODEL_READY = False
# ...

@bot.event
async def on_ready():
    print(f'Login OK: {bot.user} (ID: {bot.user.id})')

# !geminiコマンド
@bot.command()
async def gemini(ctx, *, prompt: str):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    if not GEMINI_READY:
        await ctx.send("ごめんなさい、現在AIモデルの準備ができていないため、お答えできません。")
        return
    async with ctx.typing():
        try:
            response = gemini_model.generate_content(prompt)
            await ctx.send(response.text)
        except Exception as e:
            print(f"Gemini APIエラー: {e}")
            await ctx.send(f"ごめんなさい、AIモデルとの通信中にエラーが発生しました。\n`{e}`")

# !marukofuコマンド
@bot.command()
async def marukofu(ctx):
    try: # ◀️ 消えてしまっていたメッセージ削除処理を復活させました！
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return
    sentence = text_model.make_sentence(tries=300, max_chars=140)
    if sentence:
        await ctx.send(sentence.replace(" ", ""))
    else:
        await ctx.send("ごめんなさい、学習データに基づいて文章をうまく生成できませんでした。")

# !marukofushortコマンド
@bot.command()
async def marukofushort(ctx):
    try: # ◀️ 消えてしまっていたメッセージ削除処理を復活させました！
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return
    long_sentence = text_model.make_sentence(tries=300, max_chars=140)
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

# !marukofulongコマンド
@bot.command()
async def marukofulong(ctx):
    try: # ◀️ 消えてしまっていたメッセージ削除処理を復活させました！
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return
    sentence1 = text_model.make_sentence(tries=300, max_chars=140)
    sentence2 = text_model.make_sentence(tries=300, max_chars=140)
    if sentence1 and sentence2:
        long_sentence = sentence1.replace(" ", "") + " " + sentence2.replace(" ", "")
        await ctx.send(long_sentence)
    else:
        await ctx.send("ごめんなさい、学習データに基づいて長い文章をうまく生成できませんでした。")

# !omikujiコマンド
@bot.command()
async def omikuji(ctx):
    try: # ◀️ 消えてしまっていたメッセージ削除処理を復活させました！
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    results = ["大吉 🥳", "中吉 😊", "小吉 🙂", "吉 😉", "末吉 😐", "凶 😟", "大凶 😭"]
    fortune = random.choice(results)
    await ctx.send(f'{ctx.author.display_name} さんの今日の運勢は... **{fortune}** です！')

# !createstsaymessageコマンド
@bot.command()
async def createstsaymessage(ctx, *, message: str):
    try: # ◀️ 消えてしまっていたメッセージ削除処理を復活させました！
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    await ctx.send(message)

# Botの起動
bot.run(os.environ['DISCORD_BOT_TOKEN'])


