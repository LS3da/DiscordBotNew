import discord
from discord import app_commands # ◀️ スラッシュコマンドの魔法をインポート
import os
import random
import markovify
from discord.ext import commands
from janome.tokenizer import Tokenizer
import google.generativeai as genai


# !コマンドとの決別
bot = commands.Bot(command_prefix=' ', intents=discord.Intents.all())

# ======================= Gemini APIの準備 =======================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_READY = False
LITE_GEMINI_READY = False # 軽量モデル
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)

        # 1. 安定版
        gemini_model = genai.GenerativeModel('gemini-flash-latest')
        print("Gemini モデルの準備に成功しました。")
        GEMINI_READY = True

        # 2. Gemini Liteモデルのテスト
        lite_gemini_model = genai.GenerativeModel('gemini-flash-lite-latest') # ライト版Gemini
        print("超軽量Geminiモデルの準備に成功しました。")
        LITE_GEMINI_READY = True
        
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
@bot.tree.command(name="gemini", description="博識な人に質問...")
@app_commands.describe(prompt="質問したい内容を入力してください。")
async def gemini_slash(interaction: discord.Interaction, prompt: str):
    if not GEMINI_READY:
        # ephemeral=True で、コマンド実行者にだけ見える一時的なメッセージを送る
        await interaction.response.send_message("ごめんな、現在AIモデルが完了してない。もう少しだけ待ってくれる？", ephemeral=True)
        return

    # 「考え中...」の表示を出す（こちらも実行者のみに見える）
    await interaction.response.defer(thinking=True, ephemeral=True)
    
    try:
        response = gemini_model.generate_content(prompt)
        # 最初の応答の後は followup.send を使う
        await interaction.followup.send(f"> {prompt}\n\n{response.text}")
    except Exception as e:
        print(f"Gemini APIエラー: {e}")
        await interaction.followup.send(f"> {prompt}\n\nあーあ、AIモデルとの通信中にエラーが発生しました。\n`{e}`")

# /thinkコマンド
@bot.tree.command(name="think", description="理屈から深く考える人に質問...")
@app_commands.describe(prompt="深く考えてほしいテーマを入力してください。")
async def think_slash(interaction: discord.Interaction, prompt: str):
    if not GEMINI_READY:
        await interaction.response.send_message("あーあ、現在AIモデルの準備ができていません。", ephemeral=True)
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

# /geminiliteコマンド (Gemini Flash Latestを使用)
@bot.tree.command(name="geminilite", description="超軽量なGeminiモデルに質問...")
@app_commands.describe(prompt="軽量モデルに聞きたい内容を入力してください。")
async def litegemini_slash(interaction: discord.Interaction, prompt: str):
    if not LITE_GEMINI_READY:
        await interaction.response.send_message("すんません、超軽量モデル準備できんかった...", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    
    try:
        # 💡 lite_gemini_model を呼び出す！
        response = lite_gemini_model.generate_content(prompt)
        await interaction.followup.send(f"> {prompt}\n\n{response.text}")
    except Exception as e:
        print(f"Gemini Lite APIエラー: {e}")
        await interaction.followup.send(f"> {prompt}\n\nすまねえ、軽量モデルが話聞いてくれんかった...\n`{e}`")
# ============================================================================


# --- ここから下は、これまでの「!」を使うコマンドです ---
# --- スラッシュコマンドと共存できるので、そのままで大丈夫です ---
# --- だったはずなんですが、スラッシュコマンド化されました ---

# /marukofuコマンド
@bot.tree.command(name="marukofu", description="詩人(マルコフ連鎖)が、記憶から言葉を紡ぎます。")
async def marukofu_slash(interaction: discord.Interaction):
    # 【仕事道具】秘書からの報告書(interaction)
    
    # 【仕事1】自分の命令(メッセージ)を削除する → そもそも命令が残らないので『不要』になる！

    # 【仕事2】モデルの準備ができているか確認
    if not MODEL_READY:
        # 【応答方法】報告書(interaction)を使って、依頼主に直接返事をする
        # ephemeral=True で、本人にだけ見えるようにする
        await interaction.response.send_message("ごめんなさい、現在学習モデルの準備ができていません。", ephemeral=True)
        return
        
    # 💡【新しい仕事】「今から考えます」と依頼主に伝える
    # thinking=Falseで「入力中...」は出さない
    await interaction.response.defer(thinking=False, ephemeral=False)
    
    # 【仕事3】文章を生成する
    sentence = text_model.make_sentence(tries=300, max_chars=140)
    
    # 【仕事4】結果に応じて返事をする
    # 💡 deferの後の返事は followup.send を使う
    if sentence:
        await interaction.followup.send(sentence.replace(" ", ""))
    else:
        await interaction.followup.send("ごめんなさい、学習データに基づいて文章をうまく生成できませんでした。")

# /marukofushortコマンド
@bot.tree.command(name="marukofushort", description="マルコフ連鎖による言葉を、よりコンパクトに。")
async def marukofushort_slash(interaction: discord.Interaction):
    # 【修正点1】最初の応答を、作法通り interaction.response で行う
    if not MODEL_READY:
        await interaction.response.send_message("ごめんなさい、現在学習モデルの準備ができていません。", ephemeral=True)
        return

    # 「考えます」と先に伝えておく
    await interaction.response.defer(thinking=False, ephemeral=False)
    
    # 元の文章を生成する
    long_sentence = text_model.make_sentence(tries=300, max_chars=140)
    
    sentence = None # 最終的に送信する文章を入れる変数
    if long_sentence:
        # 【修正点2】元のコードにあった「文章を短くする処理」を、ここに持ってくる
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
    
    # 【修正点3】最終的な結果を、followupで一度だけ送信する
    if sentence:
        # ここでは .replace(" ", "") は不要（clean_sentenceの時点で処理済み）
        await interaction.followup.send(sentence)
    else:
        await interaction.followup.send("ごめんなさい、学習データに基づいて短い文章をうまく生成できませんでした。")

# /marukofulongコマンド
@bot.tree.command(name="marukofulong", description="マルコフ連鎖の言葉を、より長く。")
async def marukofulong_slash(interaction: discord.Interaction):
    if not MODEL_READY:
        await interaction.response.send_message("すまねえ、現在学習モデルの準備ができていないんだ。", ephemeral=True)
        return
    await interaction.response.defer(thinking=False, ephemeral=False)
    
    
    sentence1 = text_model.make_sentence(tries=300, max_chars=140)
    sentence2 = text_model.make_sentence(tries=300, max_chars=140)
    
    if sentence1 and sentence2:
        long_sentence = sentence1.replace(" ", "") + " " + sentence2.replace(" ", "")
        await interaction.followup.send(long_sentence)
    else:
        await interaction.followup.send("すまん、学習データに基づいて長い文章をうまく生成できなかった。")

# /omikujiコマンド
@bot.tree.command(name="omikuji", description="おみくじを引いて、あなたの運気を測ろう。")
async def omikuji_slash(interaction: discord.Interaction):
    
    # 💡【ピース2】すぐに返事ができるので、defer/followupは不要！
    
    # おみくじの結果を選ぶ
    results = ["大吉 🥳", "中吉 😊", "小吉 🙂", "吉 😉", "末吉 😐", "凶 😟", "大凶 😭"]
    fortune = random.choice(results)
    
    # 💡【ピース1】ctx.author ではなく、interaction.user を使う
    user_name = interaction.user.display_name
    
    # 💡 最初の応答である send_message で、一気に結果を送る！
    await interaction.response.send_message(f'{user_name} さんの今日の運勢は... **{fortune}** です！')

# /sayコマンド (特定のロールを持つ人のみ)
@bot.tree.command(name="say", description="【管理者用】Botに代わってメッセージを送信します。")
@app_commands.describe(message="Botに話させたい内容を入力してください。")
# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ これが、権限を制限する魔法です ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
@app_commands.checks.has_role("CreatestAdmin") # ◀️ ここに、許可したいロールの名前を正確に入力します
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
async def say_slash(interaction: discord.Interaction, message: str):
    
    # 💡 ephemeral=True にすることで、コマンドの実行自体は本人にしか見えなくなる
    await interaction.response.send_message("メッセージを代理で送信しました。", ephemeral=True)
    
    # 💡 interaction.channel を使うことで、コマンドが実行されたチャンネルにメッセージを送る
    await interaction.channel.send(message)

# 権限がない場合のエラーメッセージを、優しく上書きする
@say_slash.error
async def say_slash_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message("このコマンドを使うには、もっと大切なことをしないといけない...", ephemeral=True)
    else:
        # その他のエラーは、コンソールに表示しつつ、ユーザーにも伝える
        print(error)
        await interaction.response.send_message("すまねえ、読み上げれなかったぜ...", ephemeral=True)

# Botの起動
bot.run(os.environ['DISCORD_BOT_TOKEN'])




