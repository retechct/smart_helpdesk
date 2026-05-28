from werkzeug.security import generate_password_hash
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, user="postgres",
    password="Guarana1z", dbname="smart_helpdesk"
)
cur = conn.cursor()

usuarios = [
    ("cmendoza@empresa.com", "carlos123"),
    ("agomez@empresa.com",   "ana123"),
]

for email, password in usuarios:
    phash = generate_password_hash(password)
    cur.execute("UPDATE usuarios SET password_hash=%s WHERE email=%s", (phash, email))
    print(f"✅ {email} → contraseña: {password}")

conn.commit()
conn.close()