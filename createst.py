import discord
from discord import app_commands # ◀️ スラッシュコマンドの魔法をインポート
import os
import random
import markovify
from discord.ext import commands
from discord import ui # ◀️ ボタンを使うための新しい魔法
from janome.tokenizer import Tokenizer
import google.generativeai as genai
import re
import asyncio
import unicodedata


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

# ======================= ホワイトチャンネルリストの準備 =======================
WHITE_CHANNEL_IDS = []
try:
    with open("whitechannel.txt", encoding="utf-8") as f:
        # IDを整数型に変換してリスト化
        WHITE_CHANNEL_IDS = [int(line.strip()) for line in f.readlines() if line.strip() and line.strip().isdigit()]
    print(f"ホワイトチャンネルリストの読み込みに成功しました。({len(WHITE_CHANNEL_IDS)}個)")
    WHITE_CHANNEL_READY = True
except FileNotFoundError:
    print("ホワイトチャンネルファイル 'whitechannel.txt' が見つかりません。チャンネルフィルタは無効です。")
    WHITE_CHANNEL_READY = False
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
        
        # 3. チャンネルに投稿
        await interaction.response.send_message(message)
        
        # 4. ボタンのメッセージを、誰が最後に振ったか追記して更新
        original_embed = interaction.message.embeds[0]
        original_embed.set_footer(text=f"最終実行者: {interaction.user.display_name} | {total}")
        await interaction.message.edit(embed=original_embed, view=self)


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

    # 1. 絵文字の変換と処理
    if emoji.startswith('<') and emoji.endswith('>') and ':' in emoji:
        # カスタム絵文字の場合
        processed_emoji = emoji.split(':')[1] + ':' + emoji.split(':')[2].replace('>', '')
    else:
        # 💡 標準絵文字の場合：バリエーション（毒）を抜く！
        # NFD (Normal Form D) で分解し、非スペーシングマーク（毒）を削除し、NFCで再結合する
        processed_emoji = "".join(
            c for c in unicodedata.normalize("NFD", emoji)
            if unicodedata.category(c) != "Mn" and unicodedata.category(c) != "Me"
        )
        
    # 2. Embedの作成（メッセージ投稿の準備）
    embed = discord.Embed(
        title=f"【リアクションロール】",
        description=f"**{message}**\n\n下の {emoji} でリアクションすると、\n`@{role.name}` ロールが付与/剥奪されます。",
        color=discord.Color.blue()
    )
    
    # 3. メッセージの投稿と記憶 
    panel_message = await interaction.channel.send(embed=embed) 
    
    # 4. 実行完了メッセージの送信
    await interaction.response.send_message(f"リアクションロールパネルを作成しました。\n- 絵文字: {emoji}\n- ロール: @{role.name}", ephemeral=True)
    
    # 5. Botによるリアクション (無害化された絵文字を使う！)
    await panel_message.add_reaction(processed_emoji)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # 1. 必須チェックとデータ取得（変更なし）
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    member = payload.member
    if not member: return

    channel = guild.get_channel(payload.channel_id)
    if not channel: return
    
    try:
        message = await channel.fetch_message(payload.message_id)
        if message.author.id != bot.user.id or not message.embeds:
            return
    except discord.NotFound:
        return

    embed_title = message.embeds[0].title
    
    # --------------------------------------------------------------------
    # 💡 究極の排他制御：どちらかの処理に入ったら、もう一方の処理は無視する
    # --------------------------------------------------------------------
    
    # 1. 【リアクションロール】の処理
    if embed_title == "【リアクションロール】":
        
        # ロール名抽出ロジック（省略）
        try:
            import re
            description = message.embeds[0].description
            role_match = re.search(r'`@([^`]+)`', description)
            if not role_match: return 
            role_name = role_match.group(1) 
        except Exception:
            return 

        role_to_add = discord.utils.get(guild.roles, name=role_name)
        
        # 💡 メンバーがまだロールを持っていない場合のみ付与 (二重付与対策)
        if role_to_add and member and role_to_add not in member.roles:
            
            await member.add_roles(role_to_add)
            print(f"{member.display_name} に @{role_to_add.name} を付与しました。")

            # 💡 処理は成功したが、リアクションは残す（これが作法！）

            return # 役割付与が完了したので、ここで処理を終了

        # 💡 ロールを既に持っている場合（二重リアクション）
        elif role_to_add and member and role_to_add in member.roles:
            try:
                # ユーザーが再度リアクションを付けてきた場合、Botの権限でそれを消す
                await message.remove_reaction(payload.emoji, payload.member)
            except discord.Forbidden:
                pass
            return # 役割付与は不要だが、リアクション処理は終わったので、ここで終了

    # --------------------------------------------------------------------
    # 💡 仕分けロジック 2: 【ダイスロール】の処理
    # --------------------------------------------------------------------
    # 💡 タイトルに「リアクションダイスパネル」という文言が含まれているかチェックするだけに簡略化
    if "リアクションダイスパネル" in embed_title: 
        
        # 1. Embedのフッターから隠された情報（DICEROLLとEMOJI）を抽出
        footer_text = message.embeds[0].footer.text
        if footer_text and 'DICEROLL:' in footer_text:
            try:
                # 2. 情報を解析
                diceroll_info = footer_text.split('|')[0].split(':')[1].strip()
                emoji_info = footer_text.split('|')[1].split(':')[1].strip()
                
                # 3. 押された絵文字が、パネルの絵文字と一致するかチェック
                if str(payload.emoji) == emoji_info:
                    
                    # 4. ダイスロールの実行
                    num_dice, num_sides = map(int, diceroll_info.lower().split('d'))
                    results = [random.randint(1, num_sides) for _ in range(num_dice)]
                    total = sum(results)
                    
                    # 5. 結果を全員に見える形で投稿
                    result_message = (
                        f"🎲 **{payload.member.display_name}** が {diceroll_info} を振って: **{total}** を出しました！\n"
                        f"内訳: `{results}`"
                    )
                    await channel.send(result_message)
                    
                    # 6. 究極のリアクション作法：Botがリアクションを消して、次のロールを促す
                    await message.remove_reaction(payload.emoji, payload.member)
                    return # ダイス処理が完了したので、ここで処理を終了
                    
            except Exception as e:
                print(f"ダイスロールリアクションエラー: {e}")
                pass

    # --------------------------------------------------------------------
    # 💡 仕分けロジック 3: 【チケットパネル】の処理
    # --------------------------------------------------------------------
    elif embed_title.startswith("✉️ サポートチケットの作成"):
        
        # 💡 ここで、すぐに try ブロックを開始し、全ての処理を囲む
        try:
            # 1. Embedのフッターから隠された情報（EMOJI）を抽出
            footer_text = message.embeds[0].footer.text
            if not footer_text or 'TICKET_PANEL' not in footer_text:
                return # 形式が違う場合は即座に終了

            # 2. 情報を抽出
            ticket_emoji = footer_text.split('|')[1].split(':')[1].strip()
            
            # 3. 押された絵文字が、パネルの絵文字と一致するかチェック
            if str(payload.emoji) != ticket_emoji:
                return # 絵文字が違えば即座に終了

            # 4. チャンネル名の設定
            channel_name = f"ticket-{member.name}-{member.discriminator}"
            
            # 5. チャンネルの権限を設定
            admin_role = discord.utils.get(guild.roles, name="CreatestAdmin") 
            if not admin_role: admin_role = discord.utils.get(guild.roles, name="Admin") 

            # 6. チャンネルを作成！
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False), 
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True), 
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True), 
                admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True) 
            }
        
            new_channel = await guild.create_text_channel(
                channel_name, 
                overwrites=overwrites, 
                topic=f"ユーザーID: {member.id} のサポートチケットです。相談内容: {message.embeds[0].fields[0].value}"
            )
            
            # 7. チャンネル内に最初のメッセージを投稿
            await new_channel.send(
                f"{member.mention} {admin_role.mention} さん、サポートチャンネルがオープンしました！\n"
                f"Botは管理者 {admin_role.name} の方々と、あなた（{member.display_name}）だけが、ここを見ることができます。\n"
                f"チケットを開いてくれてありがとうございます。管理者からの応答をお待ちください。"
            )
            
            # 8. Botがリアクションを消して、次のチケットを促す
            await message.remove_reaction(payload.emoji, member)
            return # 処理が完了したので、ここで終了
    
        # ❌ except が try とペアを組む
        except Exception as e:
            print(f"チケット作成エラー: {e}")
            # エラーの場合は、元のメッセージに管理者向けのエラーを追記し、元のリアクションは消さない
            original_embed = message.embeds[0]
            original_embed.add_field(name="エラー発生", value="チャンネル作成に失敗しました。（管理者向けのログを確認してください）", inline=False)
            await message.edit(embed=original_embed)
            
# リアクションが「削除」されたことを監視するイベント
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    
    # 1. 必須チェックとデータ取得（このデータ取得は絶対に省略できません！）
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    # 💡 on_raw_reaction_remove では member の情報は不確実なので、get_memberで取得する
    member = guild.get_member(payload.user_id) 
    if not member: return # メンバーがサーバーにいない場合は処理を中断

    channel = guild.get_channel(payload.channel_id)
    if not channel: return
    
    try:
        # メッセージを取得（Botの投稿かチェック）
        message = await channel.fetch_message(payload.message_id)
        if message.author.id != bot.user.id or not message.embeds:
            return
    except discord.NotFound:
        return

    embed_title = message.embeds[0].title
    
    # --------------------------------------------------------------------
    # 💡 仕分けロジック 1: 【リアクションロール】の処理
    # --------------------------------------------------------------------
    if embed_title == "【リアクションロール】":
        
        # ロール名抽出ロジック（省略）
        try:
            import re
            description = message.embeds[0].description
            role_match = re.search(r'`@([^`]+)`', description)
            if not role_match: return 
            role_name = role_match.group(1) 
        except Exception:
            return 

        role_to_remove = discord.utils.get(guild.roles, name=role_name)
        
        if role_to_remove and member:
            # 💡 メンバーからロールを剥奪！
            await member.remove_roles(role_to_remove)
            print(f"{member.display_name} から @{role_to_remove.name} を剥奪しました。")
            return # 役割剥奪が完了したので、ここで処理を終了
            
    # --------------------------------------------------------------------
    # 💡 仕分けロジック 2: 【ダイスロール】の処理
    # --------------------------------------------------------------------
    # 💡 インデントを戻し、最初の if と同じレベルにすることで、独立したチェックにする
    if "リアクションダイスパネル" in embed_title: 
        # ダイスパネルの場合、リアクションが外されたことは、無視する（処理不要）
        return
    

# /callmesコマンド：通話への参加を促す（召集令状）
@bot.tree.command(name="callmes", description="通話チャンネルへの参加を促します。")
async def callmes_slash(interaction: discord.Interaction):
    
    # 1. Botの応答は、全員に見えるようにする
    await interaction.response.defer(thinking=False, ephemeral=False)
    
    # 2. コマンドを打ったユーザーの名前とメンションを取得
    user_mention = interaction.user.mention
    user_name = interaction.user.display_name
    
    # 3. 召集令状のメッセージを構築
    message = (
        f"📣 **【通話参加者募集！】** 📣\n"
        f"**{user_mention}** さんが、通話チャンネルであなたを待っています！\n"
        f"みんなで一緒に話しませんか？\n\n"
        f"（Botがこのメッセージを代理送信しています）"
    )
    
    # 4. メッセージをチャンネルに送信
    await interaction.followup.send(message)
    
# /rollコマンド：ダイスロール機能
@bot.tree.command(name="roll", description="ダイスを振ります (例: 1d100, 3d6)。")
@app_commands.describe(diceroll="振りたいダイスの形式 (例: 1d100)")
async def roll_slash(interaction: discord.Interaction, diceroll: str):
    
    # 応答をdeferし、結果が出るまで待たせる
    await interaction.response.defer(thinking=True, ephemeral=False)
    
    try:
        # 1. 入力チェックと解析 (例: 1d100 -> [1, 100])
        if 'd' not in diceroll.lower():
            await interaction.followup.send("ごめんなさい、入力形式が正しくありません。例: `1d100`", ephemeral=True)
            return

        num_dice, num_sides = map(int, diceroll.lower().split('d'))
        
        if num_dice <= 0 or num_sides <= 1:
             await interaction.followup.send("ダイス数と面数は、1以上の整数である必要があります。", ephemeral=True)
             return
             
        if num_dice > 20 or num_sides > 1000:
            await interaction.followup.send("ダイスは最大20個、面数は最大1000までに制限しています。", ephemeral=True)
            return

        # 2. ダイスを振る
        results = [random.randint(1, num_sides) for _ in range(num_dice)]
        total = sum(results)
        
        # 3. 結果の表示
        message = (
            f"🎲 **{interaction.user.display_name} さんのダイスロール結果！**\n"
            f"**{diceroll.upper()}** の合計: **{total}**\n"
            f"内訳: `{results}`"
        )
        
        await interaction.followup.send(message)
        
    except ValueError:
        await interaction.followup.send("入力が整数ではありません。例: `1d6`", ephemeral=True)
    except Exception as e:
        print(f"Rollコマンドエラー: {e}")
        await interaction.followup.send("ダイスロール中に予期せぬエラーが発生しました。", ephemeral=True)

# /buttonrollコマンド：ボタン付きダイスロール機能
@bot.tree.command(name="reactionroll", description="リアクションを押すたびにダイスを振ります (例: 1d100)。")
@app_commands.describe(diceroll="振りたいダイスの形式 (例: 1d100)", emoji="使用する絵文字 (例: 🎲, 🎯)")
async def reactionroll_slash(interaction: discord.Interaction, diceroll: str, emoji: str = "🎲"):
    
    await interaction.response.defer(thinking=False, ephemeral=False)
    
    # 1. 入力チェック (roll_slashのロジックをそのまま使用)
    if 'd' not in diceroll.lower():
        await interaction.followup.send("ごめんなさい、入力形式が正しくありません。例: `1d100`", ephemeral=True)
        return
        
    try:
        num_dice, num_sides = map(int, diceroll.lower().split('d'))
        if num_dice <= 0 or num_sides <= 1 or num_dice > 20 or num_sides > 1000:
             await interaction.followup.send("ダイス数/面数を確認してください。", ephemeral=True)
             return
    except ValueError:
        await interaction.followup.send("入力が整数ではありません。例: `1d6`", ephemeral=True)
        return
        
    # 2. 絵文字の無害化（Botがリアクションを付けられるように）
    if emoji.startswith('<') and emoji.endswith('>') and ':' in emoji:
        processed_emoji = emoji.split(':')[1] + ':' + emoji.split(':')[2].replace('>', '')
    else:
        processed_emoji = "".join(c for c in unicodedata.normalize("NFD", emoji) if unicodedata.category(c) != "Mn" and unicodedata.category(c) != "Me")

    # 3. パネルの作成と投稿
    embed = discord.Embed(
        title=f"🎲 {diceroll.upper()} リアクションダイスパネル",
        description=f"下の {emoji} でリアクションすると、**あなた専用**のダイスを振ることができます！",
        color=discord.Color.gold()
    )
    # 💡 必要な情報をEmbedのフッターに隠して記憶させる（再起動対策）
    embed.set_footer(text=f"DICEROLL:{diceroll.upper()}|EMOJI:{processed_emoji}")
    
    panel_message = await interaction.followup.send(embed=embed)
    await panel_message.add_reaction(processed_emoji)

# /ticketコマンド：チケットパネルを作成
@bot.tree.command(name="ticket", description="プライベートなサポートチャンネルを作成するためのパネルを投稿します。")
@app_commands.describe(content="相談したい内容の要約を記入してください。")
async def ticket_slash(interaction: discord.Interaction, content: str):
    
    await interaction.response.defer(thinking=False, ephemeral=False)
    
    # 1. パネルの作成
    ticket_emoji = "✉️" # チケットに使用する絵文字を固定
    
    embed = discord.Embed(
        title="✉️ サポートチケットの作成",
        description=f"下の {ticket_emoji} でリアクションすると、**あなたと管理者だけ**が見えるプライベートなチャンネルが作成されます。",
        color=discord.Color.red()
    )
    embed.add_field(name="相談内容", value=content, inline=False)
    
    # 💡 必要な情報をフッターに隠して記憶させる（再起動対策）
    # チケットの識別に使う情報はないため、EMOJIだけを隠します。
    embed.set_footer(text=f"TICKET_PANEL|EMOJI:{ticket_emoji}")
    
    # 2. メッセージ投稿とBotのリアクション
    panel_message = await interaction.followup.send(embed=embed)
    await panel_message.add_reaction(ticket_emoji)

# /helpコマンド：Botの機能一覧を表示
@bot.tree.command(name="help", description="Botの全機能と使い方を表示します。")
async def help_slash(interaction: discord.Interaction):
    
    # 💡 Botの「記憶」に、全てのコマンド情報を持たせる
    #    このリストは、あなたの提供してくださった情報から作成しました。
    commands_list = [
        ("【AI・知識】賢者の知恵と戦略", [
            ("`/gemini`", "ある程度のことを、豊かに説明。（安定版Gemini）"),
            ("`/think`", "ほとんどのことにおいて、論理的に深く考える。（戦略家）"),
            ("`/geminilite`", "超軽量なモデルに質問。（最速応答）"),
        ]),
        ("【創作・詩人】言葉と運勢", [
            ("`/marukofu`", "知っていることを、ミックスして識る。（通常）"),
            ("`/marukofulong`", "マルコフ連鎖の言葉を、より長く。（長文モード）"),
            ("`/marukofushort`", "マルコフ連鎖による言葉を、よりコンパクトに。（短文モード）"),
            ("`/omikuji`", "おみくじを引いて、あなたの運気を測ろう。"),
        ]),
        ("【管理者・運営】秩序と管理", [
            ("`/reaction`", "リアクションでロールを付与/剥奪するパネルを作成します。"),
            ("`/delete`", "指定した数のメッセージを一掃します。（最大100件）"),
            ("`/say`", "Botが代わってメッセージを送信します。"),
        ]),
        ("【その他・ユーティリティ】", [
            ("`/callmes`", "通話チャンネルへの参加を促します。（召集令状）"),
            ("`/roll`", "ダイスを振ります。(例: 1d100)"),
            ("`/buttonroll`", "ボタンダイスを出現させます。(例: 1d100)"),
        ]),
    ]
    
    # Embedの作成
    embed = discord.Embed(
        title="🌟 Bot 機能一覧とコマンドリファレンス 🌟",
        description="このBotは、知性、創造性、管理能力を兼ね備えています。\n以下の`/`コマンドで Bot の能力を呼び出してください。",
        color=discord.Color.gold()
    )
    
    # 各カテゴリをフィールドとしてEmbedに追加
    for category_name, commands_in_category in commands_list:
        field_value = ""
        for command_name, description in commands_in_category:
            field_value += f"**{command_name}**: {description}\n"
        
        embed.add_field(name=category_name, value=field_value, inline=False)
        
    # 最後の注釈
    embed.set_footer(text="Botの運用には、利用規約とプライバシーポリシーが適用されます。")

    # 応答は、全員に見えるようにする
    await interaction.response.send_message(embed=embed, ephemeral=False)

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
            await asyncio.sleep(0.9) 
            
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
    # 1. Bot自身のメッセージ、およびコマンド処理は無視
    if message.author.bot:
        return

    # 💡 スラッシュコマンドではなく、レガシーコマンド（!）をチェックする（必要に応じて）
    await bot.process_commands(message) 

    # --------------------------------------------------------------------
    # 2. チャンネル・ホワイトリストによる「最優先の出口」チェック
    # --------------------------------------------------------------------
    if WHITE_CHANNEL_READY and message.channel.id in WHITE_CHANNEL_IDS:
        # 規制対象外のチャンネルなので、処理を即座に終了！
        # print(f"✅ チャンネルID {message.channel.id} はホワイトリストのため、フィルタをスキップします。") # ログが多すぎるのでコメントアウト
        return 
    
    # --------------------------------------------------------------------
    # 3. 禁止ワードフィルター（Black/Whiteリスト）チェック
    # --------------------------------------------------------------------
    if not BADWORDS_READY:
        return
        
    content = message.content.lower() 
    
    for badword in BADWORDS_LIST:
        target_word = badword.lower()

        # 1. 究極のパワープレイ：部分一致で一発検知
        if target_word in content:
            
            # 2. 門番のチェック：このメッセージはホワイトリストに守られているか？
            is_safe = False
            if WHITELIST_READY:
                for safe_word in WHITELIST_LIST:
                    if safe_word in content:
                        # 無害な単語が含まれていたら、今回は見逃す！
                        is_safe = True
                        break
                
            if is_safe:
                # print(f"✅ ホワイトリストの単語を含むため、{target_word}の検知をスキップしました。")
                continue # 処理を中断し、次の禁止ワードのチェックに移る

            # 3. 門番を突破した場合、実行：メッセージを削除
            try:
                await message.delete()
            except (discord.errors.NotFound, discord.errors.Forbidden):
                pass
            
            # 4. 警告DMを送信
            try:
                await message.author.send(
                    f"⚠️ **【警告】** サーバー内で禁止されている単語『{badword}』が含まれていましたので、あなたのメッセージは削除されました。"
                )
            except discord.Forbidden:
                pass
                
            # 5. 処理を終了 (一つでも禁止ワードが見つかれば、メッセージは削除済みなのでOK)
            return




# Botの起動
bot.run(os.environ['DISCORD_BOT_TOKEN'])

















