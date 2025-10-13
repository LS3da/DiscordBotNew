import discord
import os
import random
import markovify
from discord.ext import commands
from janome.tokenizer import Tokenizer # 👈 日本語対応のために Janome をインポート

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

# トークナイザー関数を定義（markovifyに渡すための分かち書き関数）
def japanese_tokenizer(text):
    # Janomeで形態素解析を行い、単語をリストにして返す
    return t.tokenize(text, wakati=True)

try:
    with open("text.txt", encoding="utf-8") as f:
        text = f.read()

    # ======================= ここからが修正箇所です =======================

    # 1. Janomeを使ってテキスト全体を単語ごとに区切り、スペースで連結する
    #    例：「今日は晴れです」 -> "今日 は 晴れ です"
    tokenized_text = " ".join(japanese_tokenizer(text))

    # 2. スペースで区切られたテキストをmarkovifyに渡してモデルを生成する
    #    エラーの原因だった`tokenizer=...`の引数を削除
    text_model = markovify.Text(tokenized_text, state_size=1)
    
    # ======================= ここまでが修正箇所です =======================

    print("マルコフモデルの構築に成功しました。")
    MODEL_READY = True
except FileNotFoundError:
    print("学習データ 'text.txt' が見つかりません。マルコフコマンドは使用できません。")
    MODEL_READY = False
except Exception as e:
    # 構築失敗の原因を特定しやすくするために、エラー内容を具体的に出力
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
    # 削除失敗エラーを無視する処理（NotFound/Forbidden対応）
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    
    # モデルが正常に構築されていない場合はエラーメッセージを送信して終了
    if not MODEL_READY:
        await ctx.send("ごめんなさい、現在学習モデルの準備ができていないため、文章を生成できません。")
        return

    # 新しい文章を生成（最大100文字、100回試行）
    # 💡 .replace(" ", "") を追加して、生成された文章のスペースを削除
    sentence = text_model.make_sentence(tries=100, max_chars=100)
    
    if sentence:
        # 生成された文章は "単語 単語 単語" のようになっているので、スペースを削除して自然な日本語にする
        await ctx.send(sentence.replace(" ", ""))
    else:
        await ctx.send("ごめんなさい、学習データに基づいて文章をうまく生成できませんでした。")


# !omikujiコマンド：おみくじを引く
@bot.command()
async def omikuji(ctx):
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
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
    try:
        await ctx.message.delete()
    except (discord.errors.NotFound, discord.errors.Forbidden):
        pass
    await ctx.send(message)

# Botの起動
bot.run(os.environ['DISCORD_BOT_TOKEN'])
