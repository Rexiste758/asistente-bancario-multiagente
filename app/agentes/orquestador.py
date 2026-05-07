import json
import logging
import re
from typing import Any

from app.agentes.agentes_proceso import crear_agente_por_proceso
from app.agentes.catalogo_procesos import (
    detectar_proceso_por_texto,
    listar_catalogo,
    obtener_proceso,
)
from app.llm.cliente_llm import ClienteLLM
from app.memoria.memoria_conversacional import memoria_conversacional
from app.modelos import FuenteTrazabilidad, RespuestaAgente, SolicitudAgente

logger = logging.getLogger(__name__)

ACCIONES_PERMITIDAS = {"orientacion", "usar_memoria", "usar_proceso", "sin_proceso"}
PROCESOS_PERMITIDOS = {"A", "B", "C", "D", "E", "NINGUNO"}
CONFIANZAS_PERMITIDAS = {"alta", "media", "baja"}
TIPOS_SIN_PROCESO_PERMITIDOS = {
    "fuera_alcance",
    "ambiguo",
    "falta_contexto",
    "no_aplica",
}


class OrquestadorAgentes:
    """
    Orquestador principal del asistente multiagente.

    Controla el flujo conversacional:
    - recibe el body de solicitud;
    - revisa memoria por conversation_id;
    - usa catálogo como evidencia de ruteo;
    - usa un LLM clasificador controlado para decidir la ruta;
    - coordina al agente especializado correspondiente.
    """

    def __init__(self) -> None:
        self.cliente_llm = ClienteLLM()

    def atender(self, solicitud: SolicitudAgente) -> RespuestaAgente:
        pregunta = solicitud.message.text.strip()
        conversation_id = solicitud.conversation_id

        memoria_conversacional.agregar_mensaje(
            conversation_id=conversation_id,
            rol="usuario",
            contenido=pregunta,
        )

        logger.info(
            "Orquestador recibió solicitud | conversation_id=%s | user_id=%s",
            conversation_id,
            solicitud.user_id,
        )

        decision_ruta = self._clasificar_ruta_con_llm(
            pregunta=pregunta,
            conversation_id=conversation_id,
        )

        fuentes = decision_ruta["fuentes"]

        if decision_ruta["accion"] == "orientacion":
            respuesta = self._responder_orientacion(solicitud, fuentes)
            memoria_conversacional.agregar_mensaje(
                conversation_id=conversation_id,
                rol="asistente",
                contenido=respuesta.answer,
            )
            return respuesta

        if (
            decision_ruta["accion"] == "sin_proceso"
            or decision_ruta["proceso_id"] is None
        ):
            respuesta = self._responder_sin_proceso(
                solicitud=solicitud,
                decision_ruta=decision_ruta,
                fuentes=fuentes,
            )
            memoria_conversacional.agregar_mensaje(
                conversation_id=conversation_id,
                rol="asistente",
                contenido=respuesta.answer,
            )
            return respuesta

        proceso_id = decision_ruta["proceso_id"]
        proceso = obtener_proceso(proceso_id)

        if proceso is None:
            respuesta = self._responder_sin_proceso(
                solicitud=solicitud,
                decision_ruta=decision_ruta,
                fuentes=fuentes,
            )
            memoria_conversacional.agregar_mensaje(
                conversation_id=conversation_id,
                rol="asistente",
                contenido=respuesta.answer,
            )
            return respuesta

        agente = crear_agente_por_proceso(proceso_id)
        resultado_agente = agente.responder(pregunta)

        fuentes.extend(resultado_agente["sources"])

        memoria_conversacional.actualizar_proceso(
            conversation_id=conversation_id,
            proceso_id=resultado_agente["process_id"],
            proceso_nombre=resultado_agente["process_name"],
        )

        memoria_conversacional.actualizar_herramienta(
            conversation_id=conversation_id,
            herramienta=", ".join(resultado_agente["tools_used"]),
        )

        memoria_conversacional.agregar_mensaje(
            conversation_id=conversation_id,
            rol="asistente",
            contenido=resultado_agente["answer"],
        )

        logger.info(
            "Orquestador completó respuesta | conversation_id=%s | proceso=%s | agente=%s | tools=%s",
            conversation_id,
            resultado_agente["process_id"],
            resultado_agente["agent_used"],
            resultado_agente["tools_used"],
        )

        return RespuestaAgente(
            conversation_id=conversation_id,
            answer=resultado_agente["answer"],
            process_id=resultado_agente["process_id"],
            process_name=resultado_agente["process_name"],
            agent_used=resultado_agente["agent_used"],
            tools_used=resultado_agente["tools_used"],
            sources=[
                FuenteTrazabilidad(
                    type=fuente["type"],
                    details=fuente["details"],
                )
                for fuente in fuentes
            ],
        )

    def _clasificar_ruta_con_llm(
        self,
        pregunta: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Clasifica la intención conversacional.

        El LLM no responde al usuario aquí. Solo decide la ruta:
        - orientacion
        - usar_memoria
        - usar_proceso
        - sin_proceso
        """
        estado_memoria = memoria_conversacional.obtener_resumen(conversation_id)
        deteccion_catalogo = detectar_proceso_por_texto(pregunta)

        mensajes = self._crear_mensajes_clasificador_ruta(
            pregunta=pregunta,
            estado_memoria=estado_memoria,
            deteccion_catalogo=deteccion_catalogo,
        )

        resultado_llm = self.cliente_llm.generar_respuesta(
            mensajes=mensajes,
            temperatura=0.0,
            max_tokens=350,
        )

        try:
            decision_cruda = self._extraer_json(resultado_llm["respuesta"])
            decision = self._validar_decision_ruta(
                decision=decision_cruda,
                estado_memoria=estado_memoria,
            )

        except Exception as error:
            logger.warning(
                "No se pudo validar la ruta del orquestador. Error=%s",
                error,
            )

            decision = {
                "accion": "sin_proceso",
                "proceso_id": None,
                "motivo": "No fue posible clasificar la ruta con suficiente seguridad.",
                "confianza": "baja",
                "tipo_sin_proceso": "falta_contexto",
            }

        trazabilidad_llm = resultado_llm["trazabilidad"]
        trazabilidad_llm["details"]["usage"] = "clasificador_ruta_orquestador"
        trazabilidad_llm["details"]["decision"] = {
            "accion": decision["accion"],
            "proceso_id": decision["proceso_id"],
            "motivo": decision["motivo"],
            "confianza": decision["confianza"],
            "tipo_sin_proceso": decision.get("tipo_sin_proceso", "no_aplica"),
        }

        trazabilidad_orquestador = {
            "type": "orchestrator",
            "details": {
                "routing_action": decision["accion"],
                "selected_process_id": decision["proceso_id"],
                "reason": decision["motivo"],
                "confidence": decision["confianza"],
                "out_of_scope_type": decision.get(
                    "tipo_sin_proceso",
                    "no_aplica",
                ),
                "memory_state": estado_memoria,
                "catalog_detection": deteccion_catalogo,
            },
        }

        decision["fuentes"] = [
            trazabilidad_orquestador,
            trazabilidad_llm,
        ]

        return decision

    def _crear_mensajes_clasificador_ruta(
        self,
        pregunta: str,
        estado_memoria: dict[str, Any],
        deteccion_catalogo: dict[str, Any],
    ) -> list[dict[str, str]]:
        procesos = "\n".join(
            (
                f"{proceso.proceso_id}: {proceso.nombre} | "
                f"agente={proceso.agente} | documento={proceso.documento_rag}"
            )
            for proceso in listar_catalogo()
        )

        system_prompt = (
            "Eres un clasificador de ruta para un asistente multiagente interno de BANCOMEX. "
            "No respondas la pregunta del usuario. "
            "Solo decide qué debe hacer el orquestador. "
            "Devuelve exclusivamente JSON válido, sin markdown ni texto adicional."
        )

        user_prompt = f"""
Procesos disponibles:
{procesos}

Acciones permitidas:
- orientacion: el usuario pregunta qué puede hacer el asistente, pide ayuda general o procesos disponibles.
- usar_memoria: la pregunta depende claramente del proceso anterior de la misma conversación.
- usar_proceso: la pregunta menciona claramente un proceso A-E.
- sin_proceso: no hay suficiente información, está fuera de alcance o requiere aclaración.

Cuando uses "sin_proceso", clasifica también el motivo en tipo_sin_proceso:
- fuera_alcance: la pregunta pide información que no pertenece a procesos operativos internos, por ejemplo ingresos, ventas, utilidades, estados financieros, acciones, precios, nómina, información corporativa o temas externos.
- ambiguo: la pregunta parece pedir ayuda operativa, pero no indica proceso suficiente.
- falta_contexto: la pregunta depende de algo previo, pero no hay memoria suficiente.
- no_aplica: úsalo cuando la acción no sea sin_proceso.

Reglas:
- Usa el catálogo como evidencia, no como verdad absoluta.
- Si el catálogo detecta un proceso claro y la pregunta no depende de memoria, normalmente usa "usar_proceso".
- Si la pregunta actual no menciona proceso pero la memoria tiene ultimo_proceso_id, usa "usar_memoria" cuando sea razonable.
- Si el usuario pide capacidades generales, usa "orientacion".
- Si no puedes decidir con seguridad, usa "sin_proceso".
- Si la pregunta es sobre ingresos, ventas, utilidades, estados financieros, acciones, precios, nómina o información corporativa, usa "sin_proceso" con tipo_sin_proceso "fuera_alcance".
- No inventes procesos fuera de A, B, C, D o E.

Estado de memoria conversacional:
{json.dumps(estado_memoria, ensure_ascii=False)}

Detección del catálogo:
{json.dumps(deteccion_catalogo, ensure_ascii=False)}

Pregunta del usuario:
{pregunta}

Devuelve exactamente este JSON:
{{
  "accion": "usar_proceso",
  "proceso_id": "A",
  "motivo": "motivo breve",
  "confianza": "alta",
  "tipo_sin_proceso": "no_aplica"
}}
"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _validar_decision_ruta(
        self,
        decision: dict[str, Any],
        estado_memoria: dict[str, Any],
    ) -> dict[str, Any]:
        accion = str(decision.get("accion", "sin_proceso")).strip().lower()
        proceso_id = str(decision.get("proceso_id", "NINGUNO")).strip().upper()
        motivo = str(decision.get("motivo", "")).strip()
        confianza = str(decision.get("confianza", "baja")).strip().lower()
        tipo_sin_proceso = str(
            decision.get("tipo_sin_proceso", "no_aplica")
        ).strip().lower()

        if accion not in ACCIONES_PERMITIDAS:
            accion = "sin_proceso"

        if proceso_id not in PROCESOS_PERMITIDOS:
            proceso_id = "NINGUNO"

        if confianza not in CONFIANZAS_PERMITIDAS:
            confianza = "baja"

        if tipo_sin_proceso not in TIPOS_SIN_PROCESO_PERMITIDOS:
            tipo_sin_proceso = "no_aplica"

        proceso_final = None

        if accion == "orientacion":
            proceso_final = None
            tipo_sin_proceso = "no_aplica"

        elif accion == "usar_memoria":
            ultimo_proceso_id = estado_memoria.get("ultimo_proceso_id")

            if proceso_id in {"A", "B", "C", "D", "E"}:
                proceso_final = proceso_id
            elif ultimo_proceso_id:
                proceso_final = ultimo_proceso_id
            else:
                accion = "sin_proceso"
                proceso_final = None
                tipo_sin_proceso = "falta_contexto"
                motivo = (
                    motivo
                    or "Se intentó usar memoria, pero no existe proceso previo en la conversación."
                )

        elif accion == "usar_proceso":
            if proceso_id in {"A", "B", "C", "D", "E"} and confianza != "baja":
                proceso_final = proceso_id
                tipo_sin_proceso = "no_aplica"
            else:
                accion = "sin_proceso"
                proceso_final = None
                if tipo_sin_proceso == "no_aplica":
                    tipo_sin_proceso = "ambiguo"

        else:
            accion = "sin_proceso"
            proceso_final = None
            if tipo_sin_proceso == "no_aplica":
                tipo_sin_proceso = "ambiguo"

        return {
            "accion": accion,
            "proceso_id": proceso_final,
            "motivo": motivo or "Ruta clasificada por el orquestador.",
            "confianza": confianza,
            "tipo_sin_proceso": tipo_sin_proceso,
        }

    def _responder_orientacion(
        self,
        solicitud: SolicitudAgente,
        fuentes: list[dict[str, Any]],
    ) -> RespuestaAgente:
        procesos = "\n".join(
            f"- {proceso.proceso_id}: {proceso.nombre}"
            for proceso in listar_catalogo()
        )

        respuesta = (
            "Puedo ayudarte con procesos operativos internos de BANCOMEX. "
            "Puedo explicar procedimientos documentados, consultar datos estructurados "
            "como área responsable, tiempo promedio de resolución, canal de atención "
            "o nivel de criticidad, y conservar contexto dentro de esta conversación.\n\n"
            f"Procesos disponibles:\n{procesos}"
        )

        return RespuestaAgente(
            conversation_id=solicitud.conversation_id,
            answer=respuesta,
            process_id=None,
            process_name=None,
            agent_used="OrquestadorAgentes",
            tools_used=[],
            sources=[
                FuenteTrazabilidad(type=fuente["type"], details=fuente["details"])
                for fuente in fuentes
            ],
        )

    def _responder_sin_proceso(
        self,
        solicitud: SolicitudAgente,
        decision_ruta: dict[str, Any],
        fuentes: list[dict[str, Any]],
    ) -> RespuestaAgente:
        procesos = ", ".join(
            f"{proceso.proceso_id}: {proceso.nombre}"
            for proceso in listar_catalogo()
        )

        tipo_sin_proceso = decision_ruta.get("tipo_sin_proceso", "ambiguo")

        if tipo_sin_proceso == "fuera_alcance":
            respuesta = (
                "No cuento con información para responder esa consulta, porque mi alcance "
                "está limitado a procesos operativos internos de BANCOMEX. "
                "Puedo ayudarte con aclaraciones bancarias, cancelación de productos, "
                "incidencias operativas, actualización de datos del cliente o quejas internas."
            )

        elif tipo_sin_proceso == "falta_contexto":
            respuesta = (
                "Necesito un poco más de contexto para ayudarte. "
                "Indícame si tu consulta se relaciona con aclaraciones bancarias, "
                "cancelación de productos, incidencias operativas, actualización de datos "
                "del cliente o quejas internas."
            )

        else:
            respuesta = (
                "Puedo ayudarte, pero necesito saber a cuál proceso se refiere tu consulta. "
                f"Los procesos disponibles son: {procesos}."
            )

        return RespuestaAgente(
            conversation_id=solicitud.conversation_id,
            answer=respuesta,
            process_id=None,
            process_name=None,
            agent_used="OrquestadorAgentes",
            tools_used=[],
            sources=[
                FuenteTrazabilidad(type=fuente["type"], details=fuente["details"])
                for fuente in fuentes
            ],
        )

    def _extraer_json(self, texto: str) -> dict[str, Any]:
        texto_limpio = texto.strip()

        if texto_limpio.startswith("```"):
            texto_limpio = re.sub(r"^```json\s*", "", texto_limpio)
            texto_limpio = re.sub(r"^```\s*", "", texto_limpio)
            texto_limpio = re.sub(r"\s*```$", "", texto_limpio)

        inicio = texto_limpio.find("{")
        fin = texto_limpio.rfind("}")

        if inicio == -1 or fin == -1:
            raise ValueError("La respuesta del clasificador no contiene JSON.")

        return json.loads(texto_limpio[inicio : fin + 1])
