import sys
sys.path.insert(0, r"e:\miscol\AISing\ai-sing-server")
from app.services.security import hash_password
import sqlite3

conn = sqlite3.connect(r"e:\miscol\AISing\ai-sing-server\data\ai_sing.db")
c = conn.cursor()

token = "KGiozIC3wsy0VEfxJB--nRPR_Avx3eY4UHoUPWsqu5Guoi6YAK2LKhTimol5AMH7"
pw_hash = hash_password("003177")

c.execute("SELECT id FROM users WHERE username = ?", ("13666003177",))
row = c.fetchone()
if row:
    c.execute(
        "UPDATE users SET password_hash = ?, active_token = ?, credits = 9999, status = 'active', phone = '13666003177' WHERE id = ?",
        (pw_hash, token, row[0]),
    )
    print("Updated user 13666003177")
else:
    from datetime import datetime
    c.execute(
        "INSERT INTO users (id, username, password_hash, phone, credits, active_token, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (12, "13666003177", pw_hash, "13666003177", 9999, token, "active", str(datetime.now())),
    )
    print("Inserted user 13666003177 with id=12")

# Update testuser and test password
pw_123456 = hash_password("123456")
pw_test = hash_password("test")
c.execute("UPDATE users SET password_hash = ?, status = 'active', credits = 9999 WHERE username = 'testuser'", (pw_123456,))
c.execute("UPDATE users SET password_hash = ?, status = 'active', credits = 9999 WHERE username = 'test'", (pw_test,))

conn.commit()

c.execute("SELECT id, username, phone, credits, active_token FROM users")
print("Current users in DB:", c.fetchall())
conn.close()
