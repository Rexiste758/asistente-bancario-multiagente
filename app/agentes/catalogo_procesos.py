import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReglaProceso:
    """
    Define señales de ruteo para un proceso.

    Las frases fuertes pesan más porque representan una intención más clara.
    Los términos de apoyo ayudan, pero por sí solos no deberían decidir siempre.
    """

    proceso_id: str
    nombre: str
    agente: str
    frases_fuertes: list[str] = field(default_factory=list)
    terminos_apoyo: list[str] = field(default_factory=list)


CATALOGO_PROCESOS: dict[str, ReglaProceso] = {
    "A": ReglaProceso(
        proceso_id="A",
        nombre="Atención de aclaraciones bancarias",
        agente="AgenteAclaraciones",
        frases_fuertes=[
        "levantar una aclaracion",
        "presentar una aclaracion",
        "hacer una aclaracion",
        "aclaracion bancaria",
        "proceso de aclaraciones",
        "aclaraciones por cargos",
        "aclaraciones por cargos no reconocidos",
        "cargo no reconocido",
        "cargos no reconocidos",
        "movimiento no reconocido",
        "movimientos no reconocidos",
        "operacion no reconocida",
        "cobro no reconocido",
        "cobros no reconocidos",
        "cobro incorrecto",
        "pago no aplicado",
        "transferencia no aplicada",
        ],
        terminos_apoyo=[
            "aclaracion",
            "aclaraciones",
            "cargo",
            "cargos",
            "abono",
            "abonos",
            "comision",
            "comisiones",
            "movimiento",
            "movimientos",
            "pago",
            "pagos",
            "transferencia",
            "transferencias",
            "deposito",
            "depositos",
            "retiro",
            "retiros",
            "cobro",
            "cobros",
        ],
    ),
    "B": ReglaProceso(
        proceso_id="B",
        nombre="Cancelación de productos financieros",
        agente="AgenteCancelacion",
        frases_fuertes=[
            "cancelar una tarjeta",
            "cancelar mi tarjeta",
            "cancelar una cuenta",
            "cancelar mi cuenta",
            "cerrar una cuenta",
            "cerrar mi cuenta",
            "dar de baja mi tarjeta",
            "dar de baja una tarjeta",
            "dar de baja un producto",
            "cancelar producto",
            "cancelacion de producto",
            "cancelacion de productos",
        ],
        terminos_apoyo=[
            "cancelacion",
            "cancelar",
            "cierre",
            "cerrar",
            "baja",
            "producto",
            "productos",
            "cuenta",
            "tarjeta",
            "servicio",
            "servicios",
            "saldo pendiente",
            "producto financiero",
        ],
    ),
    "C": ReglaProceso(
        proceso_id="C",
        nombre="Escalamiento de incidencias operativas",
        agente="AgenteIncidencias",
        frases_fuertes=[
            "el sistema marca error",
            "sistema marca error",
            "no me deja terminar",
            "no deja terminar la operacion",
            "no puedo completar la operacion",
            "falla del sistema",
            "error en sistema",
            "bloqueo operativo",
            "levantar incidencia",
            "escalar incidencia",
            "mesa de ayuda",
        ],
        terminos_apoyo=[
            "incidencia",
            "incidencias",
            "falla",
            "fallas",
            "error",
            "errores",
            "sistema",
            "sistemas",
            "bloqueo",
            "soporte",
            "rechazo",
            "indisponibilidad",
            "lentitud",
            "operacion detenida",
        ],
    ),
    "D": ReglaProceso(
        proceso_id="D",
        nombre="Actualización de datos del cliente",
        agente="AgenteDatosCliente",
        frases_fuertes=[
            "actualizar datos",
            "actualizar mis datos",
            "cambiar domicilio",
            "actualizar domicilio",
            "cambiar correo",
            "actualizar correo",
            "cambiar telefono",
            "actualizar telefono",
            "modificar datos fiscales",
            "actualizar datos fiscales",
            "corregir datos del cliente",
            "mantenimiento de clientes",
        ],
        terminos_apoyo=[
            "actualizacion",
            "actualizar",
            "datos",
            "dato",
            "cliente",
            "domicilio",
            "telefono",
            "correo",
            "email",
            "fiscal",
            "identificacion",
            "nombre",
            "actividad economica",
        ],
    ),
    "E": ReglaProceso(
        proceso_id="E",
        nombre="Gestión de quejas internas",
        agente="AgenteQuejas",
        frases_fuertes=[
            "levantar una queja",
            "presentar una queja",
            "hacer una queja",
            "registrar una queja",
            "quiero quejarme",
            "queja interna",
            "inconformidad interna",
            "trato inadecuado",
            "demora injustificada",
            "incumplimiento de procedimiento",
        ],
        terminos_apoyo=[
            "queja",
            "quejas",
            "inconformidad",
            "cumplimiento",
            "calidad",
            "trato",
            "demora",
            "demoras",
            "reincidencia",
            "desviacion",
            "desviaciones",
            "atencion recibida",
        ],
    ),
}


PESO_FRASE_FUERTE = 5
PESO_TERMINO_APOYO = 1

# Umbrales para decidir si el catálogo tiene confianza suficiente.
SCORE_MINIMO_CLARO = 5
MARGEN_MINIMO_ENTRE_CANDIDATOS = 3


def normalizar_texto(texto: str) -> str:
    """
    Convierte texto a minúsculas y elimina acentos.

    Esto permite comparar "aclaración" contra "aclaracion".
    """
    texto_minusculas = texto.lower()
    texto_sin_acentos = unicodedata.normalize("NFD", texto_minusculas)

    return "".join(
        caracter
        for caracter in texto_sin_acentos
        if unicodedata.category(caracter) != "Mn"
    )


def obtener_proceso(proceso_id: str) -> ReglaProceso | None:
    return CATALOGO_PROCESOS.get(proceso_id.strip().upper())


def listar_catalogo() -> list[ReglaProceso]:
    return list(CATALOGO_PROCESOS.values())


def _evaluar_proceso(texto_normalizado: str, proceso: ReglaProceso) -> dict:
    frases_detectadas = []
    terminos_detectados = []

    for frase in proceso.frases_fuertes:
        frase_normalizada = normalizar_texto(frase)

        if frase_normalizada in texto_normalizado:
            frases_detectadas.append(frase)

    for termino in proceso.terminos_apoyo:
        termino_normalizado = normalizar_texto(termino)

        if termino_normalizado in texto_normalizado:
            terminos_detectados.append(termino)

    score = (
        len(frases_detectadas) * PESO_FRASE_FUERTE
        + len(terminos_detectados) * PESO_TERMINO_APOYO
    )

    return {
        "proceso_id": proceso.proceso_id,
        "nombre": proceso.nombre,
        "agente": proceso.agente,
        "score": score,
        "frases_fuertes_detectadas": frases_detectadas,
        "terminos_apoyo_detectados": terminos_detectados,
    }


def _evaluar_confianza(candidatos: list[dict]) -> dict:
    candidatos_con_score = [
        candidato for candidato in candidatos if candidato["score"] > 0
    ]

    if not candidatos_con_score:
        return {
            "es_claro": False,
            "motivo_confianza": "No hubo señales suficientes en el catálogo.",
        }

    ganador = candidatos_con_score[0]
    segundo = candidatos_con_score[1] if len(candidatos_con_score) > 1 else None

    tiene_frase_fuerte = len(ganador["frases_fuertes_detectadas"]) > 0
    score_ganador = ganador["score"]
    score_segundo = segundo["score"] if segundo else 0
    margen = score_ganador - score_segundo

    if tiene_frase_fuerte and margen >= MARGEN_MINIMO_ENTRE_CANDIDATOS:
        return {
            "es_claro": True,
            "motivo_confianza": (
                "Se detectó una frase fuerte de intención y el proceso ganador "
                "supera claramente a otros candidatos."
            ),
        }

    if tiene_frase_fuerte and segundo is None:
        return {
            "es_claro": True,
            "motivo_confianza": (
                "Se detectó una frase fuerte de intención sin procesos competidores."
            ),
        }

    if score_ganador >= SCORE_MINIMO_CLARO and margen >= MARGEN_MINIMO_ENTRE_CANDIDATOS:
        return {
            "es_claro": True,
            "motivo_confianza": (
                "El proceso ganador tiene score suficiente y margen claro "
                "frente al segundo candidato."
            ),
        }

    return {
        "es_claro": False,
        "motivo_confianza": (
            "Hay señales, pero no son suficientemente claras. "
            "Conviene usar el clasificador LLM o pedir aclaración."
        ),
    }


def detectar_proceso_por_texto(texto_usuario: str) -> dict:
    """
    Detecta el proceso más probable usando reglas simples y trazables.

    Importante:
    El catálogo no es verdad absoluta. Si la señal no es clara, el orquestador
    debe usar el LLM clasificador o pedir aclaración al usuario.
    """
    texto_normalizado = normalizar_texto(texto_usuario)

    candidatos = [
        _evaluar_proceso(texto_normalizado, proceso)
        for proceso in CATALOGO_PROCESOS.values()
    ]

    candidatos_ordenados = sorted(
        candidatos,
        key=lambda item: item["score"],
        reverse=True,
    )

    candidatos_con_score = [
        candidato for candidato in candidatos_ordenados if candidato["score"] > 0
    ]

    confianza = _evaluar_confianza(candidatos_ordenados)

    if not candidatos_con_score:
        return {
            "proceso_detectado": None,
            "es_claro": False,
            "requiere_llm": True,
            "motivo": "El catálogo no encontró señales suficientes.",
            "motivo_confianza": confianza["motivo_confianza"],
            "candidatos": [],
        }

    mejor = candidatos_con_score[0]

    if not confianza["es_claro"]:
        return {
            "proceso_detectado": {
                "proceso_id": mejor["proceso_id"],
                "nombre": mejor["nombre"],
                "agente": mejor["agente"],
                "score": mejor["score"],
                "frases_fuertes_detectadas": mejor["frases_fuertes_detectadas"],
                "terminos_apoyo_detectados": mejor["terminos_apoyo_detectados"],
            },
            "es_claro": False,
            "requiere_llm": True,
            "motivo": (
                "El catálogo encontró señales, pero no tiene confianza suficiente "
                "para decidir por sí solo."
            ),
            "motivo_confianza": confianza["motivo_confianza"],
            "candidatos": candidatos_con_score,
        }

    return {
        "proceso_detectado": {
            "proceso_id": mejor["proceso_id"],
            "nombre": mejor["nombre"],
            "agente": mejor["agente"],
            "score": mejor["score"],
            "frases_fuertes_detectadas": mejor["frases_fuertes_detectadas"],
            "terminos_apoyo_detectados": mejor["terminos_apoyo_detectados"],
        },
        "es_claro": True,
        "requiere_llm": False,
        "motivo": "Proceso detectado con confianza suficiente usando catálogo.",
        "motivo_confianza": confianza["motivo_confianza"],
        "candidatos": candidatos_con_score,
    }