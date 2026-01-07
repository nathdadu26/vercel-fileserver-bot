#!/usr/bin/env python3
"""
Setup webhook for Telegram Bot on Vercel
Run this ONCE after deploying to Vercel
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("FILE_SERVER_BOT_TOKEN")
VERCEL_URL = input("Enter your Vercel deployment URL (e.g., https://your-bot.vercel.app): ").strip()

# Remove trailing slash
VERCEL_URL = VERCEL_URL.rstrip('/')

# Set webhook
webhook_url = f"{VERCEL_URL}/api/webhook"
api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

print(f"\n🔧 Setting webhook to: {webhook_url}")

response = requests.post(api_url, json={"url": webhook_url})
result = response.json()

if result.get("ok"):
    print("✅ Webhook set successfully!")
    print(f"📌 Webhook URL: {webhook_url}")
    
    # Get webhook info
    info_response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
    info = info_response.json()
    
    if info.get("ok"):
        webhook_info = info.get("result", {})
        print(f"\n📊 Webhook Info:")
        print(f"   URL: {webhook_info.get('url')}")
        print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
        print(f"   Last error: {webhook_info.get('last_error_message', 'None')}")
else:
    print(f"❌ Failed to set webhook: {result.get('description')}")
    
print("\n✨ Bot is now ready on Vercel!")
