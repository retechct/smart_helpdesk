"""
app.py – Smart HelpDesk v2
Incluye: registro, login, tickets por usuario, conversación técnico↔cliente
"""

from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from azure_service  import analizar_texto
from business_rules import aplicar_reglas
from ticket_dal     import (
    crear_ticket, actualizar_ticket_ia,
    obtener_tickets_ordenados, obtener_tickets_por_usuario,
    obtener_ticket_por_id, cerrar_ticket,
    obtener_id_equipo, obtener_usuarios,
    registrar_usuario, login_usuario, obtener_departamentos,
    agregar_mensaje, obtener_mensajes,
)

app = Flask(__name__)
app.secret_key = "helpdesk-secret-2024"

MSG_BIENVENIDA = (
    "¡Hola! 👋 Tu ticket ha sido recibido correctamente. "
    "Nuestro equipo de soporte ya fue notificado y estará revisando tu caso. "
    "Te responderemos a la brevedad. ¡Gracias por tu paciencia!"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def usuario_logueado():
    return session.get("usuario_id") is not None

def es_tecnico():
    return session.get("rol") == "Tecnico"

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not usuario_logueado():
            flash("Debes iniciar sesión primero.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def tecnico_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not usuario_logueado() or not es_tecnico():
            flash("Acceso restringido a técnicos.", "danger")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        usuario  = login_usuario(email, password)
        if usuario:
            session["usuario_id"] = usuario["id"]
            session["nombre"]     = usuario["nombre"]
            session["rol"]        = usuario["rol"]
            if usuario["rol"] == "Tecnico":
                return redirect(url_for("dashboard_tecnico"))
            return redirect(url_for("dashboard_cliente"))
        flash("Credenciales incorrectas.", "danger")
    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    departamentos = obtener_departamentos()
    if request.method == "POST":
        nombre  = request.form.get("nombre", "").strip()
        email   = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        dep_id  = request.form.get("departamento_id")
        if not all([nombre, email, password, dep_id]):
            flash("Completa todos los campos.", "danger")
        else:
            uid = registrar_usuario(nombre, email, password, int(dep_id))
            if uid:
                flash("¡Cuenta creada! Ya puedes iniciar sesión.", "success")
                return redirect(url_for("login"))
            else:
                flash("El correo ya está registrado.", "danger")
    return render_template("registro.html", departamentos=departamentos)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Dashboard Cliente ─────────────────────────────────────────────────────────

@app.route("/")
@login_required
def dashboard_cliente():
    if es_tecnico():
        return redirect(url_for("dashboard_tecnico"))
    tickets = obtener_tickets_por_usuario(session["usuario_id"])
    return render_template("dashboard_cliente.html", tickets=tickets)


@app.route("/ticket/nuevo", methods=["POST"])
@login_required
def crear_ticket_route():
    asunto      = request.form.get("asunto", "").strip()
    descripcion = request.form.get("descripcion", "").strip()

    if not asunto or not descripcion:
        flash("Completa todos los campos.", "danger")
        return redirect(url_for("dashboard_cliente"))

    try:
        ticket_id = crear_ticket(asunto, descripcion, session["usuario_id"])

        # Mensaje de bienvenida automático (sistema)
        agregar_mensaje(ticket_id, None, MSG_BIENVENIDA, es_sistema=True)

        # Pipeline IA
        resultado_ia = analizar_texto(descripcion)
        sentimiento  = resultado_ia["sentimiento"]
        entidades    = resultado_ia["entidades"]

        reglas        = aplicar_reglas(descripcion, sentimiento, entidades)
        prioridad     = reglas["prioridad"]
        equipo_nombre = reglas["equipo_nombre"]

        equipo_id   = obtener_id_equipo(equipo_nombre)
        tecnologias = ", ".join(entidades) if entidades else "N/A"
        actualizar_ticket_ia(ticket_id, sentimiento, prioridad, tecnologias, equipo_id)

        flash(f"✅ Ticket registrado. Prioridad asignada: {prioridad}", "success")
    except Exception as e:
        flash(f"❌ Error al procesar el ticket: {str(e)}", "danger")

    return redirect(url_for("dashboard_cliente"))


@app.route("/ticket/<ticket_id>")
@login_required
def ver_ticket(ticket_id):
    ticket   = obtener_ticket_por_id(ticket_id)
    mensajes = obtener_mensajes(ticket_id)
    if not ticket:
        flash("Ticket no encontrado.", "danger")
        return redirect(url_for("dashboard_cliente"))
    # Solo el dueño o técnico puede ver
    if not es_tecnico() and ticket["solicitante_id"] != session["usuario_id"]:
        flash("No tienes acceso a este ticket.", "danger")
        return redirect(url_for("dashboard_cliente"))
    return render_template("conversacion.html", ticket=ticket, mensajes=mensajes)


@app.route("/ticket/<ticket_id>/mensaje", methods=["POST"])
@login_required
def enviar_mensaje(ticket_id):
    contenido = request.form.get("contenido", "").strip()
    if contenido:
        agregar_mensaje(ticket_id, session["usuario_id"], contenido)
    return redirect(url_for("ver_ticket", ticket_id=ticket_id))


@app.route("/ticket/<ticket_id>/cerrar", methods=["POST"])
@tecnico_required
def cerrar_ticket_route(ticket_id):
    cerrar_ticket(ticket_id)
    flash("Ticket cerrado correctamente.", "success")
    return redirect(url_for("dashboard_tecnico"))


# ── Dashboard Técnico ─────────────────────────────────────────────────────────

@app.route("/tecnico")
@tecnico_required
def dashboard_tecnico():
    tickets = obtener_tickets_ordenados()
    return render_template("dashboard_tecnico.html", tickets=tickets)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)