"""
Motor de Reglas de Negocio
"""

_KEYWORDS_CRITICA = {
    "servidor", "base de datos", "producción", "produccion", "red",
    "database", "server", "network", "timeout",
}

_KEYWORDS_DEVOPS = {
    "github", "código", "codigo", "docker", "despliegue", "pipeline",
    "git", "deploy", "ci", "devops", "jenkins", "gitlab",
}

_KEYWORDS_MESA_AYUDA = {
    "contraseña", "contrasena", "acceso", "licencia", "mouse", "pantalla",
    "instalación", "instalacion", "password", "login", "teclado", "impresora",
}

EQUIPO_INFRA   = "Equipo de Infraestructura y Redes"
EQUIPO_DEVOPS  = "Equipo de Desarrollo / DevOps"
EQUIPO_MESA    = "Mesa de Ayuda - Soporte Técnico"
EQUIPO_GENERAL = "Soporte TI General"


def _contiene(texto_lower, entidades_lower, keywords):
    for kw in keywords:
        if kw in texto_lower:
            return True
    for ent in entidades_lower:
        if any(kw in ent for kw in keywords):
            return True
    return False


def aplicar_reglas(descripcion: str, sentimiento: str, entidades: list) -> dict:
    t = descripcion.lower()
    e = [x.lower() for x in entidades]

    # Regla 1 – Crítica
    if sentimiento == "NEGATIVE" and _contiene(t, e, _KEYWORDS_CRITICA):
        return {"prioridad": "1-CRÍTICA", "equipo_nombre": EQUIPO_INFRA}

    # Regla 2 – Media / DevOps
    if sentimiento in ("NEGATIVE", "NEUTRAL") and _contiene(t, e, _KEYWORDS_DEVOPS):
        return {"prioridad": "2-MEDIA", "equipo_nombre": EQUIPO_DEVOPS}

    # Regla 3 – Baja / Mesa de Ayuda
    if _contiene(t, e, _KEYWORDS_MESA_AYUDA):
        return {"prioridad": "3-BAJA", "equipo_nombre": EQUIPO_MESA}

    # Regla 4 – Default
    return {"prioridad": "3-BAJA", "equipo_nombre": EQUIPO_GENERAL}