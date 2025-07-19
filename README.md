# 📈 Nifty 50 + F&O Screener using Dhan API

Scans bullish setups across Nifty 50 and F&O stocks using:
- Daily close above 88 EMA + KC Upper + RSI > 60
- 1H pullback and RSI crossover
- Runs Mon–Fri, 09:15–15:30 IST via Render cron

## ✅ Setup
1. Push to GitHub
2. Deploy as cron job on Render
3. Set environment variables:
   - DHAN_API_KEY
   - DHAN_CLIENT_ID
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
