"""
ticket_dal.py – Data Access Layer
Soporta: tickets, mensajes/conversación, registro de usuarios
"""

import uuid
import psycopg2
import psycopg2.extras
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
from werkzeug.security import generate_password_hash, check_password_hash


def _get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
        sslmode="require"      # ← esta línea es clave para Neon
    )

# ── Usuarios ──────────────────────────────────────────────────────────────────

def registrar_usuario(nombre, email, password, departamento_id=1):
    """Registra un nuevo empleado. Retorna el id o None si el email ya existe."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # rol_id=1 = Empleado
        cur.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, rol_id, departamento_id) "
            "VALUES (%s, %s, %s, 1, %s) RETURNING id",
            (nombre, email, generate_password_hash(password), departamento_id),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return None
    finally:
        conn.close()


def login_usuario(email, password):
    """Valida credenciales. Retorna dict con datos del usuario o None."""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT u.id, u.nombre, u.email, r.nombre_rol AS rol, u.password_hash "
            "FROM usuarios u JOIN roles r ON u.rol_id = r.id WHERE u.email = %s",
            (email,),
        )
        row = cur.fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return dict(row)
        return None
    finally:
        conn.close()


def obtener_usuarios():
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT u.id, u.nombre, u.email, r.nombre_rol AS rol "
            "FROM usuarios u JOIN roles r ON u.rol_id = r.id"
        )
        return cur.fetchall()
    finally:
        conn.close()


def obtener_departamentos():
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, nombre_dep FROM departamentos ORDER BY id")
        return cur.fetchall()
    finally:
        conn.close()


# ── Tickets ───────────────────────────────────────────────────────────────────

def crear_ticket(asunto, descripcion, solicitante_id):
    ticket_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tickets (id, asunto, descripcion, estado, solicitante_id) "
            "VALUES (%s, %s, %s, 'Abierto', %s)",
            (ticket_id, asunto, descripcion, solicitante_id),
        )
        conn.commit()
    finally:
        conn.close()
    return ticket_id


def actualizar_ticket_ia(ticket_id, sentimiento, prioridad, tecnologias, equipo_id):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE tickets SET ia_sentimiento=%s, ia_prioridad=%s, "
            "ia_tecnologias=%s, equipo_id=%s WHERE id=%s",
            (sentimiento, prioridad, tecnologias, equipo_id, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()


def obtener_tickets_ordenados():
    """Todos los tickets abiertos, ordenados por prioridad."""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                t.id, t.asunto, t.descripcion, t.estado, t.creado_el,
                t.ia_sentimiento, t.ia_prioridad, t.ia_tecnologias,
                u.nombre        AS solicitante,
                d.nombre_dep    AS departamento,
                e.nombre_equipo AS equipo,
                (SELECT COUNT(*) FROM mensajes m WHERE m.ticket_id = t.id) AS num_mensajes
            FROM tickets t
            JOIN usuarios      u ON t.solicitante_id = u.id
            JOIN departamentos d ON u.departamento_id = d.id
            LEFT JOIN equipos_soporte e ON t.equipo_id = e.id
            ORDER BY
                CASE t.ia_prioridad
                    WHEN '1-CRÍTICA' THEN 1  WHEN '1-CRITICA' THEN 1
                    WHEN '2-MEDIA'   THEN 2
                    WHEN '3-BAJA'    THEN 3
                    ELSE 4
                END ASC,
                t.creado_el DESC
        """)
        return cur.fetchall()
    finally:
        conn.close()


def obtener_tickets_por_usuario(usuario_id):
    """Tickets del empleado autenticado."""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                t.id, t.asunto, t.descripcion, t.estado, t.creado_el,
                t.ia_sentimiento, t.ia_prioridad, t.ia_tecnologias,
                e.nombre_equipo AS equipo,
                (SELECT COUNT(*) FROM mensajes m WHERE m.ticket_id = t.id) AS num_mensajes
            FROM tickets t
            LEFT JOIN equipos_soporte e ON t.equipo_id = e.id
            WHERE t.solicitante_id = %s
            ORDER BY t.creado_el DESC
        """, (usuario_id,))
        return cur.fetchall()
    finally:
        conn.close()


def obtener_ticket_por_id(ticket_id):
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT t.*, u.nombre AS solicitante, u.email AS solicitante_email,
                   d.nombre_dep AS departamento, e.nombre_equipo AS equipo
            FROM tickets t
            JOIN usuarios u ON t.solicitante_id = u.id
            JOIN departamentos d ON u.departamento_id = d.id
            LEFT JOIN equipos_soporte e ON t.equipo_id = e.id
            WHERE t.id = %s
        """, (ticket_id,))
        return cur.fetchone()
    finally:
        conn.close()


def cerrar_ticket(ticket_id):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE tickets SET estado='Cerrado' WHERE id=%s", (ticket_id,))
        conn.commit()
    finally:
        conn.close()


def obtener_id_equipo(nombre_equipo):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM equipos_soporte WHERE nombre_equipo = %s", (nombre_equipo,)
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# ── Mensajes / Conversación ───────────────────────────────────────────────────

def agregar_mensaje(ticket_id, autor_id, contenido, es_sistema=False):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO mensajes (ticket_id, autor_id, contenido, es_sistema) "
            "VALUES (%s, %s, %s, %s)",
            (ticket_id, autor_id, contenido, es_sistema),
        )
        conn.commit()
    finally:
        conn.close()


def obtener_mensajes(ticket_id):
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT m.id, m.contenido, m.creado_el, m.es_sistema,
                   u.nombre AS autor, r.nombre_rol AS rol_autor
            FROM mensajes m
            LEFT JOIN usuarios u ON m.autor_id = u.id
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE m.ticket_id = %s
            ORDER BY m.creado_el ASC
        """, (ticket_id,))
        return cur.fetchall()
    finally:
        conn.close()