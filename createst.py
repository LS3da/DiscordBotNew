import discord
from discord import app_commands # ◀️ スラッシュコマンドの魔法をインポート
import os
import random
import markovify
from discord.ext import commands
from janome.tokenizer import Tokenizer
import google.generativeai as genai
import re
import asyncio


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

# ======================= 禁止ワードリストの準備 =======================
BADWORDS_LIST = []
try:
    with open("badwords.txt", encoding="utf-8") as f:
        # 改行と空行を削除してリスト化
        BADWORDS_LIST = [word.strip() for word in f.readlines() if word.strip()]
    print(f"禁止ワードリストの読み込みに成功しました。({len(BADWORDS_LIST)}個)")
    BADWORDS_READY = True
except FileNotFoundError:
    print("禁止ワードファイル 'badwords.txt' が見つかりません。禁止ワードフィルタは無効です。")
    BADWORDS_READY = False
# =====================================================================

# ======================= ホワイトリストの準備 =======================
WHITELIST_LIST = []
try:
    with open("whitelist.txt", encoding="utf-8") as f:
        WHITELIST_LIST = [word.strip().lower() for word in f.readlines() if word.strip()]
    print(f"ホワイトリストの読み込みに成功しました。({len(WHITELIST_LIST)}個)")
    WHITELIST_READY = True
except FileNotFoundError:
    print("ホワイトリストファイル 'whitelist.txt' が見つかりません。ホワイトリスト機能は無効です。")
    WHITELIST_READY = False
# =======================================================================

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
@bot.tree.command(name="gemini", description="ある程度の事を、豊かに説明。")
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
        await interaction.followup.send(f"> {prompt}\n\nあ、すみません。AIモデルとの通信中にエラーが発生しちゃった。\n`{e}`")

# /thinkコマンド
@bot.tree.command(name="think", description="ほとんどの事において、しっかり考える。")
@app_commands.describe(prompt="深く考えてほしいテーマを入力してください。")
async def think_slash(interaction: discord.Interaction, prompt: str):
    if not GEMINI_READY:
        await interaction.response.send_message("あーあ、現在AIモデルの準備ができていないんだ。", ephemeral=True)
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
@bot.tree.command(name="geminilite", description="条件反射で答える人に質問...")
@app_commands.describe(prompt="聞きたい内容を入力してください。")
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
        await interaction.followup.send(f"> {prompt}\n\nすまねえ、軽量モデルが話聞いてくれんかったんよ...\n`{e}`")
# ============================================================================


# --- ここから下は、これまでの「!」を使うコマンドです ---
# --- スラッシュコマンドと共存できるので、そのままで大丈夫です ---
# --- だったはずなんですが、スラッシュコマンド化されました ---

# /marukofuコマンド
@bot.tree.command(name="marukofu", description="知っている事を、ミックスして識る。")
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
        await interaction.followup.send("ごめんね、学習データに基づいて短い文章をうまく生成できませんでした。")

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

# /reactionコマンド：リアクションロールパネルを作成
@bot.tree.command(name="reaction", description="【ロール管理者権限】リアクションでロールを付与/剥奪するパネルを作成します。")
@app_commands.describe(
    message="パネルに表示するメッセージ (例: ゲームする人はリアクション！)",
    emoji="リアクションに使用する絵文字 (例: 💣)",
    role="付与/剥奪するロールを選択してください。"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def reaction_slash(interaction: discord.Interaction, message: str, emoji: str, role: discord.Role):
    
    # 運営からの実行完了メッセージ（本人にしか見えない）
    await interaction.response.send_message(f"リアクションロールパネルを作成しました。\n- 絵文字: {emoji}\n- ロール: @{role.name}", ephemeral=True)
    
    # Botが投稿する募集パネルの作成
    embed = discord.Embed(
        title=f"【リアクションロール】",
        description=f"**{message}**\n\n下の {emoji} でリアクションすると、\n`@{role.name}` ロールが付与/剥奪されます。",
        color=discord.Color.blue()
    )
    
    # 実際にパネルをチャンネルに投稿し、そのメッセージ情報を取得
    panel_message = await interaction.channel.send(embed=embed)
    
    # 最後に、Bot自身がそのメッセージに指定された絵文字でリアクションする
    await panel_message.add_reaction(emoji)

# リアクションが「追加」されたことを監視するイベント
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Bot自身のリアクションは無視する
    if payload.user_id == bot.user.id:
        return

    # どのサーバー(guild)で、どのチャンネル(channel)で、どのメッセージ(message)かを取得
    # guild, channel, message が None になる可能性への対処を追加
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    channel = guild.get_channel(payload.channel_id)
    if not channel: return
    
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        return # メッセージが見つからない場合は処理を中断
    
    # リアクションされたメッセージがBotの投稿で、かつEmbed形式(パネル)でなければ無視
    if message.author.id != bot.user.id or not message.embeds:
        return
        
    # Embedのタイトルが「【リアクションロール】」でなければ無視
    if message.embeds[0].title != "【リアクションロール】":
        return

    # Embedの説明文から、どの絵文字とどのロールが対応しているかを読み取る
    description = message.embeds[0].description
    try:
        target_emoji = description.split("下の ")[1].split(" ")[0]
        role_name = description.split("`@")[1].split("`")[0]
    except IndexError:
        return # 説明文の形式が違う場合は無視

    # 押されたリアクションが、パネルで指定された絵文字と一致するか確認
    if str(payload.emoji) == target_emoji:
        role_to_add = discord.utils.get(guild.roles, name=role_name)
        member = guild.get_member(payload.user_id)
        
        if role_to_add and member:
            # メンバーにロールを付与！
            await member.add_roles(role_to_add)
            print(f"{member.display_name} に @{role_to_add.name} を付与しました。")

# リアクションが「削除」されたことを監視するイベント
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    # Bot自身のリアクションは無視する
    if payload.user_id == bot.user.id:
        return

    # どのサーバー(guild)で、どのチャンネル(channel)で、どのメッセージ(message)かを取得
    # guild, channel, message が None になる可能性への対処を追加
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    channel = guild.get_channel(payload.channel_id)
    if not channel: return
    
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.NotFound:
        return # メッセージが見つからない場合は処理を中断
    
    # リアクションされたメッセージがBotの投稿で、かつEmbed形式(パネル)でなければ無視
    if message.author.id != bot.user.id or not message.embeds:
        return
        
    # Embedのタイトルが「【リアクションロール】」でなければ無視
    if message.embeds[0].title != "【リアクションロール】":
        return

    # Embedの説明文から、どの絵文字とどのロールが対応しているかを読み取る
    description = message.embeds[0].description
    try:
        target_emoji = description.split("下の ")[1].split(" ")[0]
        role_name = description.split("`@")[1].split("`")[0]
    except IndexError:
        return # 説明文の形式が違う場合は無視

    # 押されたリアクションが、パネルで指定された絵文字と一致するか確認
    if str(payload.emoji) == target_emoji:
        role_to_remove = discord.utils.get(guild.roles, name=role_name)
        member = guild.get_member(payload.user_id)
        
        if role_to_remove and member:
            # メンバーからロールを剥奪！
            await member.remove_roles(role_to_remove)
            print(f"{member.display_name} から @{role_to_remove.name} を剥奪しました。")

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
        await interaction.response.send_message("このコマンドを使うには、もっと大切なことをしないといけないんだ...", ephemeral=True)
    else:
        # その他のエラーは、コンソールに表示しつつ、ユーザーにも伝える
        print(error)
        await interaction.response.send_message("読み上げる時に、何故かカンペが破れちまった。", ephemeral=True)

# /deleteコマンド：指定された数のメッセージを削除（パージ）
@bot.tree.command(name="delete", description="【管理者用】指定した数のメッセージを一掃します。（最大100件）")
@app_commands.describe(count="削除したいメッセージの数（1～100）")
@app_commands.checks.has_permissions(manage_messages=True) 
async def delete_slash(interaction: discord.Interaction, count: int):
    
    if count < 1 or count > 100:
        await interaction.response.send_message("ごめんなさい、削除できるメッセージの数は1件から100件までです。", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    
    deleted_count = 0
    
    try:
        # 1. チャンネルのメッセージを、指定された数だけ取得 (Botの実行メッセージを含むため、+1)
        #    history()は、Botの実行場所（チャンネル）のメッセージ履歴を取得します
        messages = []
        async for message in interaction.channel.history(limit=count + 1):
            messages.append(message)
        
        # 2. 律儀な削除ループを実行（最後のBotのメッセージは消さない）
        for message in messages:
            # 💡 コマンド実行メッセージは削除せず、スキップする
            if message.id == interaction.id:
                continue

            # 3. メッセージを削除
            await message.delete()
            deleted_count += 1
            
            # 4. 究極の Rate Limit 回避策：削除の間に「優雅な一呼吸」を挟む
            #    0.5秒の停止は、Botの律儀さを保ちつつ、Discordに優しくする最適な間隔です
            await asyncio.sleep(0.5) 
            
        # 5. 成功報告（全員に見えるように）
        await interaction.followup.send(
            f"🧹 **一掃完了！**\n"
            f"管理者 {interaction.user.display_name} の命令により、最新の **{deleted_count}件** のメッセージが削除されました。",
            ephemeral=False
        )

    except Exception as e:
        print(f"Deleteコマンドエラー: {e}")
        await interaction.followup.send(f"ごめんなさい、メッセージの一掃中にエラーが発生しました。\n`{e}`", ephemeral=True)

# 権限がない場合のエラーメッセージ
@delete_slash.error
async def delete_slash_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("このコマンドを使うには、『メッセージの管理』という特別な許可が必要です。", ephemeral=True)
    else:
        # その他のエラーは、優しく対処
        await interaction.response.send_message("一掃する巻物の詠唱に失敗しました。", ephemeral=True)

# （/reactionコマンドのイベント関数の下、Bot起動の bot.run の上あたりに追加）

# メッセージが投稿されるたびに呼び出される「守護者」イベント
@bot.event
async def on_message(message):
    # ... (Bot自身のメッセージ、process_commandsなどは省略) ...
    
    # ----------------------------------------------------
    # 実戦的かつ論理的な禁止ワードチェック
    # ----------------------------------------------------
    content = message.content.lower() 
    
    for badword in BADWORDS_LIST:
        target_word = badword.lower()

        # 1. 究極のパワープレイ：部分一致で一発検知
        if target_word in content:
            
            # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ ここに「門番」を追加します ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
            
            # 2. 門番のチェック：このメッセージはホワイトリストに守られているか？
            if WHITELIST_READY:
                is_safe = False
                for safe_word in WHITELIST_LIST:
                    if safe_word in content:
                        # 禁止ワードと同じメッセージ内に「無害な単語」が含まれている場合、
                        # それは誤爆の可能性が高いので、今回は見逃す！
                        is_safe = True
                        break
                
                if is_safe:
                    print(f"✅ ホワイトリストの単語を含むため、{target_word}の検知をスキップしました。")
                    continue # 処理を中断し、次のメッセージを待つ
            
            # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

            # 3. 門番を突破した場合、実行：メッセージを削除
            try:
                await message.delete()
            except (discord.errors.NotFound, discord.errors.Forbidden):
                pass
            
            # ... (警告DMの処理は省略) ...
                
            return

# Botの起動
bot.run(os.environ['DISCORD_BOT_TOKEN'])













