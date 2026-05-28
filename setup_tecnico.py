"""
setup_tecnico.py
Ejecuta este script UNA SOLA VEZ para crear el usuario técnico con contraseña.
Uso: python setup_tecnico.py
"""

from werkzeug.security import generate_password_hash
import psycopg2
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

TECNICO_NOMBRE = "Soporte TI"
TECNICO_EMAIL  = "soporte@empresa.com"
TECNICO_PASS   = "tecnico123"   # ← Cambia esto en producción

def main():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, dbname=DB_NAME,
    )
    cur = conn.cursor()

    # Asegura que exista la columna password_hash
    cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)")

    # Crea tabla mensajes si no existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id         SERIAL PRIMARY KEY,
            ticket_id  VARCHAR(36) NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            autor_id   INT REFERENCES usuarios(id) ON DELETE SET NULL,
            contenido  TEXT NOT NULL,
            es_sistema BOOLEAN DEFAULT FALSE,
            creado_el  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Equipo faltante
    cur.execute(
        "INSERT INTO equipos_soporte (nombre_equipo) VALUES ('Soporte TI General') ON CONFLICT DO NOTHING"
    )

    # Hash seguro
    phash = generate_password_hash(TECNICO_PASS)

    # Inserta o actualiza técnico
    cur.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, rol_id, departamento_id) "
        "VALUES (%s, %s, %s, 2, 2) ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash",
        (TECNICO_NOMBRE, TECNICO_EMAIL, phash),
    )

    conn.commit()
    conn.close()
    print(f"✅ Técnico listo: {TECNICO_EMAIL} / {TECNICO_PASS}")
    print("   (Cambia la contraseña antes de pasar a producción)")


if __name__ == "__main__":
    main()