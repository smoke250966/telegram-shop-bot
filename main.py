import staypresent
import os

# ده عشان Koyeb يشوف البوت شغال
staypresent.web.json({"status": "running"})
staypresent.run("bot.py", port=int(os.getenv("PORT", 8080)))