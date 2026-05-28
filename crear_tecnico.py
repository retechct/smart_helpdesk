"""
crear_tecnico.py
Crea un nuevo técnico o resetea la contraseña de uno existente.
Usa las variables de entorno del .env (compatible con Neon/PostgreSQL remoto).

Uso:
    python crear_tecnico.py
"""

from werkzeug.security import generate_password_hash
import psycopg2
import sys
import os

# ── Carga el .env ──────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env cargado correctamente")
except ImportError:
    print("⚠️  python-dotenv no instalado. Usando variables de entorno del sistema.")

DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = int(os.getenv("DB_PORT", 5432))
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME     = os.getenv("DB_NAME", "smart_helpdesk")
DB_SSLMODE  = os.getenv("DB_SSLMODE", "require")

# ── Configuración del nuevo técnico ───────────────────────────────────────────
# 👇 EDITA AQUÍ los datos del técnico que quieres crear/resetear
TECNICOS = [
    {
        "nombre":          "Soporte TI",
        "email":           "soporte@empresa.com",
        "password":        "tecnico123",
        "departamento_id": 2,   # TI
    },
    # Descomenta y edita para agregar más técnicos:
    # {
    #     "nombre":          "Ana Técnico",
    #     "email":           "ana.tecnico@empresa.com",
    #     "password":        "ana_pass_2024",
    #     "departamento_id": 2,
    # },
]
# ──────────────────────────────────────────────────────────────────────────────


def verificar_config():
    """Verifica que las variables de entorno estén configuradas."""
    faltantes = [v for v in ["DB_HOST", "DB_USER", "DB_PASSWORD"] if not os.getenv(v)]
    if faltantes:
        print(f"\n❌ ERROR: Faltan variables de entorno: {', '.join(faltantes)}")
        print("   Asegúrate de tener un archivo .env con:")
        print("   DB_HOST=<tu-host-neon>")
        print("   DB_USER=<tu-usuario>")
        print("   DB_PASSWORD=<tu-contraseña>")
        print("   DB_NAME=smart_helpdesk")
        sys.exit(1)


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
        sslmode=DB_SSLMODE,
    )


def obtener_rol_tecnico(cur):
    """Obtiene el id del rol 'Tecnico', lo crea si no existe."""
    cur.execute("SELECT id FROM roles WHERE nombre_rol = 'Tecnico'")
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO roles (nombre_rol) VALUES ('Tecnico') RETURNING id")
    return cur.fetchone()[0]


def obtener_departamento(cur, dep_id):
    """Verifica que el departamento exista."""
    cur.execute("SELECT id, nombre_dep FROM departamentos WHERE id = %s", (dep_id,))
    return cur.fetchone()


def crear_o_actualizar_tecnico(cur, tecnico, rol_id):
    """Inserta el técnico o actualiza su contraseña si ya existe."""
    phash = generate_password_hash(tecnico["password"])

    cur.execute("SELECT id, nombre FROM usuarios WHERE email = %s", (tecnico["email"],))
    existente = cur.fetchone()

    if existente:
        # Ya existe → solo resetea la contraseña y asegura que sea técnico
        cur.execute(
            "UPDATE usuarios SET password_hash = %s, rol_id = %s, nombre = %s WHERE email = %s",
            (phash, rol_id, tecnico["nombre"], tecnico["email"]),
        )
        return "actualizado", existente[0]
    else:
        # No existe → lo crea
        cur.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, rol_id, departamento_id) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (tecnico["nombre"], tecnico["email"], phash, rol_id, tecnico["departamento_id"]),
        )
        return "creado", cur.fetchone()[0]


def main():
    print("\n🔧 Smart HelpDesk – Gestión de Técnicos")
    print("=" * 45)

    verificar_config()

    print(f"\n📡 Conectando a: {DB_HOST} / {DB_NAME}...")
    try:
        conn = get_conn()
        print("✅ Conexión exitosa\n")
    except Exception as e:
        print(f"❌ No se pudo conectar: {e}")
        sys.exit(1)

    cur = conn.cursor()

    try:
        rol_id = obtener_rol_tecnico(cur)
        print(f"   Rol 'Tecnico' → id={rol_id}")

        for tec in TECNICOS:
            dep = obtener_departamento(cur, tec["departamento_id"])
            dep_nombre = dep[1] if dep else f"id={tec['departamento_id']} (no encontrado)"

            accion, uid = crear_o_actualizar_tecnico(cur, tec, rol_id)

            estado = "✅ CREADO" if accion == "creado" else "🔄 ACTUALIZADO"
            print(f"\n{estado}: {tec['nombre']}")
            print(f"   Email:        {tec['email']}")
            print(f"   Contraseña:   {tec['password']}")
            print(f"   Departamento: {dep_nombre}")
            print(f"   Usuario ID:   {uid}")

        conn.commit()
        print("\n✅ Cambios guardados en la base de datos.")
        print("\n⚠️  RECUERDA: cambia las contraseñas antes de pasar a producción.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()