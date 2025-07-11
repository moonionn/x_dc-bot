import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading
import asyncio
from datetime import datetime

# 載入環境變數
load_dotenv()

# Flask 應用程式
app = Flask(__name__)

# 設定intents
intents = discord.Intents.default()
intents.message_content = True

# 建立bot實例
bot = commands.Bot(command_prefix='!', intents=intents)

# 儲存已發送的訊息
sent_messages = {}

@bot.event
async def on_ready():
    print(f'{bot.user} 已經準備好了！')
    print(f'Bot ID: {bot.user.id}')

@bot.event  
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command(name='test')
async def test_command(ctx):
    await ctx.send('Bot運作正常！')

# Flask 路由 - 接收 IFTTT 的請求
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """接收 IFTTT 的 webhook"""
    try:
        data = request.json
        print(f"收到 webhook: {data}")
        
        # 從 IFTTT 取得資料
        tweet_text = data.get('tweet_text', '')
        tweet_url = data.get('tweet_url', '')
        tweet_id = data.get('tweet_id', str(datetime.now().timestamp()))
        username = data.get('username', 'Unknown')
        
        # 格式化訊息
        message_content = f"**來自 @{username} 的推文**\n{tweet_text}\n\n🔗 {tweet_url}"
        
        # 設定要發送的頻道ID
        channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
        
        # 使用 asyncio 發送訊息
        asyncio.run_coroutine_threadsafe(
            send_to_discord(channel_id, message_content, tweet_id),
            bot.loop
        )
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Webhook 錯誤: {str(e)}")
        return jsonify({"error": str(e)}), 500

async def send_to_discord(channel_id, content, tweet_id):
    """發送訊息到 Discord"""
    channel = bot.get_channel(channel_id)
    if channel:
        msg = await channel.send(content)
        sent_messages[tweet_id] = msg
        print(f"已發送推文 {tweet_id}")
    else:
        print(f"找不到頻道 {channel_id}")

@app.route('/health')
def health_check():
    """健康檢查端點"""
    return jsonify({"status": "healthy"}), 200

def run_flask():
    """在獨立執行緒運行 Flask"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("錯誤: 找不到DISCORD_TOKEN")
    else:
        # 在新執行緒啟動 Flask
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        # 啟動 Discord bot
        bot.run(token)