import discord
from discord import app_commands # ◀️ スラッシュコマンドの魔法をインポート
import os
import random
import markovify
from discord.ext import commands
from janome.tokenizer import Tokenizer
import google.generativeai as genai

# Botの定義は変更なし
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# ======================= Gemini APIの準備 =======================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_READY = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-flash-latest')
        print("Geminiモデルの準備に成功しました。")
        GEMINI_READY = True
    except Exception as e:
        print(f"Geminiモデルの準備中にエラーが発生しました: {e}")
else:
    print("環境変数 'GEMINI_API_KEY' が見つかりません。Geminiコマンドは使用できません。")
# ================================================================

# ======================= マルコフ連鎖モデルの準備 =======================
MODEL_READY = False
try:
    t = Tokenizer()
    def japanese_tokenizer(text):
        return t.tokenize(text, wakati=True)
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
# =====================================================================

@bot.event
async def on_ready():
    print(f'Login OK: {bot.user} (ID: {bot.user.id})')
    # 💡 Botが起動したときに、スラッシュコマンドをDiscordに同期させる
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)}個のスラッシュコマンドを同期しました。")
    except Exception as e:
        print(f"スラッシュコマンドの同期に失敗しました: {e}")

# ======================= ここからがスラッシュコマンドです =======================

# /geminiコマンド
@bot.tree.command(name="gemini", description="賢者に質問します。")
@app_commands.describe(prompt="質問したい内容を入力してください。")
async def gemini_slash(interaction: discord.Interaction, prompt: str):
    if not GEMINI_READY:
        # ephemeral=True で、コマンド実行者にだけ見える一時的なメッセージを送る
        await interaction.response.send_message("ごめんなさい、現在AIモデルの準備ができていません。", ephemeral=True)
        return

    # 「考え中...」の表示を出す（こちらも実行者のみに見える）
    await interaction.response.defer(thinking=True, ephemeral=True)
    
    try:
        response = gemini_model.generate_content(prompt)
        # 最初の応答の後は followup.send を使う
        await interaction.followup.send(f"> {prompt}\n\n{response.text}")
    except Exception as e:
        print(f"Gemini APIエラー: {e}")
        await interaction.followup.send(f"> {prompt}\n\nごめんなさい、AIモデルとの通信中にエラーが発生しました。\n`{e}`")

# /thinkコマンド
@bot.tree.command(name="think", description="戦略家に深く思考させます。")
@app_commands.describe(prompt="深く考えてほしいテーマを入力してください。")
async def think_slash(interaction: discord.Interaction, prompt: str):
    if not GEMINI_READY:
        await interaction.response.send_message("ごめんなさい、現在AIモデルの準備ができていません。", ephemeral=True)
        return

    # こちらは全員に見えるようにする
    await interaction.response.defer(thinking=True, ephemeral=False)
    
    try:
        thinking_prompt = f"""以下の問いに対して、ステップ・バイ・ステップで深く考察し、その思考プロセスと最終的な結論を日本語で記述してください。
### 問い
{prompt}
### 思考プロセス
1. 問いの主要なキーワードを特定し、分解する。
2. """
        response = gemini_model.generate_content(thinking_prompt)
        
        # 応答にプロンプトを引用して、何についての思考か分かりやすくする
        header = f"> **テーマ:** `{prompt}`\n\n"
        
        if len(response.text) > (1950 - len(header)):
            await interaction.followup.send(header + response.text[:(1950 - len(header))] + "\n...(文字数制限のため、以下省略)...")
        else:
            await interaction.followup.send(header + response.text)
            
    except Exception as e:
        print(f"Thinkコマンドエラー: {e}")
        await interaction.followup.send(f"> **テーマ:** `{prompt}`\n\nごめんなさい、思考中にエラーが発生しました。\n`{e}`")

# ============================================================================


# --- ここから下は、これまでの「!」を使うコマンドです ---
# --- スラッシュコマンドと共存できるので、そのままで大丈夫です ---

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
    sentence = text_model.make_sentence(tries=300, max_chars=140)
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
    try:
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
