import json
import logging
import re
from typing import Any

from app.agentes.catalogo_procesos import ReglaProceso

logger = logging.getLogger(__name__)


TOOLS_PERMITIDAS = {"RAGTool", "DatabaseTool"}

CONSULTAS_BD_PERMITIDAS = {"area_responsable","tiempo_promedio_resolucion","canal_atencion","nivel_criticidad","resumen_operativo","ninguna",}

CONFIANZAS_PERMITIDAS = {"alta", "media", "baja"}


class AgenteEspecializadoBase:
    """
    Clase base para los agentes especializados de BANCOMEX.

    La lógica común vive aquí:
    - clasificar si la pregunta necesita RAG, BD o ambas herramientas;
    - consultar herramientas;
    - pedir al LLM que redacte la respuesta final;
    - devolver trazabilidad.

    Las clases concretas definen el proceso específico:
    aclaraciones, cancelación, incidencias, datos del cliente o quejas.
    """

    def __init__(self, proceso: ReglaProceso) -> None:
        self.proceso = proceso

        # Se inicializan bajo demanda para evitar cargar componentes pesados
        # cuando no se usan.
        self._herramienta_bd = None
        self._herramienta_rag = None
        self._cliente_llm = None

    @property
    def herramienta_bd(self):
        if self._herramienta_bd is None:
            from app.herramientas.herramienta_bd import HerramientaBD

            self._herramienta_bd = HerramientaBD()

        return self._herramienta_bd

    @property
    def herramienta_rag(self):
        if self._herramienta_rag is None:
            from app.herramientas.herramienta_rag import HerramientaRAG

            self._herramienta_rag = HerramientaRAG()

        return self._herramienta_rag

    @property
    def cliente_llm(self):
        if self._cliente_llm is None:
            from app.llm.cliente_llm import ClienteLLM

            self._cliente_llm = ClienteLLM()

        return self._cliente_llm

    def responder(self, pregunta: str) -> dict[str, Any]:
        """
        Responde una pregunta dentro del dominio del proceso asignado.
        """
        decision = self._clasificar_herramientas(pregunta)

        logger.info(
            "Agente especializado clasificó herramientas | agente=%s | proceso=%s | tools=%s | bd=%s",
            self.proceso.agente,self.proceso.proceso_id,decision["tools"],decision["tipo_consulta_bd"],)

        fuentes = [decision["trazabilidad"]]
        contexto_rag = ""
        contexto_bd = ""

        if "RAGTool" in decision["tools"]:
            resultado_rag = self.herramienta_rag.buscar(pregunta=pregunta,process_id=self.proceso.proceso_id,)
            fuentes.append(resultado_rag["trazabilidad"])
            contexto_rag = self._construir_contexto_rag(resultado_rag["chunks"])

        if (
            "DatabaseTool" in decision["tools"]
            and decision["tipo_consulta_bd"] != "ninguna"
        ):
            resultado_bd = self.herramienta_bd.consultar_proceso(
                proceso_id=self.proceso.proceso_id,
                tipo_consulta=decision["tipo_consulta_bd"],
            )
            fuentes.append(resultado_bd["trazabilidad"])
            contexto_bd = self._construir_contexto_bd(resultado_bd["resultado"])

        mensajes = self._crear_mensajes_respuesta_final(pregunta=pregunta,contexto_rag=contexto_rag,contexto_bd=contexto_bd,herramientas=decision["tools"],)

        resultado_llm = self.cliente_llm.generar_respuesta(mensajes)
        resultado_llm["trazabilidad"]["details"]["usage"] = "respuesta_final"
        fuentes.append(resultado_llm["trazabilidad"])

        return {
            "answer": resultado_llm["respuesta"],
            "process_id": self.proceso.proceso_id,
            "process_name": self.proceso.nombre,
            "agent_used": self.proceso.agente,
            "tools_used": decision["tools"],
            "sources": fuentes,
            "tool_decision": {"tools": decision["tools"],"tipo_consulta_bd": decision["tipo_consulta_bd"],"motivo": decision["motivo"],"confianza": decision["confianza"],
            },
        }

    def _clasificar_herramientas(self, pregunta: str) -> dict[str, Any]:
        """
        Usa un LLM clasificador controlado para decidir qué herramienta usar.

        El LLM no genera SQL. Solo puede elegir:
        - RAGTool
        - DatabaseTool
        - ambas

        Y si usa BD, solo puede elegir una consulta permitida.
        """
        mensajes = self._crear_mensajes_clasificador(pregunta)

        resultado_llm = self.cliente_llm.generar_respuesta(
            mensajes=mensajes,
            temperatura=0.0,
            max_tokens=300,
        )

        texto_respuesta = resultado_llm["respuesta"]

        try:
            decision_cruda = self._extraer_json(texto_respuesta)
            decision_validada = self._validar_decision_clasificador(decision_cruda)

        except Exception as error:
            logger.warning(
                "No se pudo validar la decisión del clasificador. "
                "Se usará RAG como respaldo. Error=%s",
                error,
            )

            decision_validada = {
                "tools": ["RAGTool"],
                "tipo_consulta_bd": "ninguna",
                "motivo": (
                    "No se pudo interpretar con seguridad la decisión del clasificador; "
                    "se usa RAG como respaldo documental."
                ),
                "confianza": "baja",
            }

        trazabilidad_llm = resultado_llm["trazabilidad"]
        trazabilidad_llm["details"]["usage"] = "clasificador_herramientas"
        trazabilidad_llm["details"]["decision"] = {"tools": decision_validada["tools"],"tipo_consulta_bd": decision_validada["tipo_consulta_bd"],"motivo": decision_validada["motivo"],"confianza": decision_validada["confianza"],
        }

        decision_validada["trazabilidad"] = trazabilidad_llm

        return decision_validada

    def _crear_mensajes_clasificador(self, pregunta: str) -> list[dict[str, str]]:
        system_prompt = (
            "Eres un clasificador interno de herramientas para un agente especializado de BANCOMEX. "
            "Tu tarea es decidir si la pregunta del usuario debe responderse con RAGTool, DatabaseTool o ambas. "
            "No respondas la pregunta del usuario. No generes SQL. "
            "Devuelve exclusivamente JSON válido, sin markdown, sin explicación adicional."
        )

        user_prompt = f"""
Proceso asignado:
- Código: {self.proceso.proceso_id}
- Nombre: {self.proceso.nombre}
- Agente: {self.proceso.agente}

Herramientas disponibles:
1. RAGTool
   Úsala cuando el usuario pida información que debe recuperarse desde documentos RAG:
   objetivo, alcance, flujo, pasos, requisitos, validaciones, escalamiento, cierre,
   explicación del proceso o reglas operativas documentadas.

2. DatabaseTool
   Úsala cuando el usuario pida datos estructurados del proceso:
   área responsable, tiempo promedio de resolución, canal de atención o nivel de criticidad.

Consultas BD permitidas:
- area_responsable
- tiempo_promedio_resolucion
- canal_atencion
- nivel_criticidad
- resumen_operativo
- ninguna

Reglas obligatorias:
- Si la pregunta pide duración, plazo, tiempo, cuánto tarda, cuánto demora, cuánto podría tardar,
  en cuánto se resuelve o tiempo estimado del proceso, usa ["DatabaseTool"] con
  tipo_consulta_bd "tiempo_promedio_resolucion".
- Si la pregunta pide área, responsable, quién atiende o quién se encarga, usa ["DatabaseTool"]
  con tipo_consulta_bd "area_responsable".
- Si la pregunta pide canal, medio, dónde se atiende o por dónde se gestiona, usa ["DatabaseTool"]
  con tipo_consulta_bd "canal_atencion".
- Si la pregunta pide criticidad, nivel crítico, qué tan crítico o prioridad operativa,
  usa ["DatabaseTool"] con tipo_consulta_bd "nivel_criticidad".
- Si la pregunta pide varios datos estructurados a la vez, usa ["DatabaseTool"]
  con tipo_consulta_bd "resumen_operativo".
- Si la pregunta pide solo explicación o procedimiento, usa ["RAGTool"] y tipo_consulta_bd "ninguna".
- Si la pregunta pide explicación y además un dato estructurado, usa ["RAGTool", "DatabaseTool"].
- Si la pregunta parece referirse a un caso particular pero pide duración, responde con el
  tiempo promedio del proceso desde BD; la respuesta final podrá aclarar que es un promedio general.
- Nunca generes SQL.
- Nunca inventes consultas fuera de la lista permitida.
- Si no estás seguro, usa ["RAGTool"] con tipo_consulta_bd "ninguna" y confianza "baja".

Ejemplos:
Pregunta: "¿Cuánto tarda?"
Respuesta:
{{"tools":["DatabaseTool"],"tipo_consulta_bd":"tiempo_promedio_resolucion","motivo":"El usuario pregunta por la duración del proceso.","confianza":"alta"}}

Pregunta: "¿Y eso cuánto podría tardar?"
Respuesta:
{{"tools":["DatabaseTool"],"tipo_consulta_bd":"tiempo_promedio_resolucion","motivo":"La pregunta es de seguimiento y solicita el tiempo promedio del proceso asignado.","confianza":"alta"}}

Pregunta: "¿Cuál es el plazo?"
Respuesta:
{{"tools":["DatabaseTool"],"tipo_consulta_bd":"tiempo_promedio_resolucion","motivo":"El usuario solicita el plazo o tiempo promedio del proceso.","confianza":"alta"}}

Pregunta: "¿Por qué canal se atiende?"
Respuesta:
{{"tools":["DatabaseTool"],"tipo_consulta_bd":"canal_atencion","motivo":"El usuario solicita el canal de atención del proceso.","confianza":"alta"}}

Pregunta: "Explícame cuándo se escala"
Respuesta:
{{"tools":["RAGTool"],"tipo_consulta_bd":"ninguna","motivo": "El usuario solicita información del procedimiento, lo cual debe recuperarse desde documentos RAG.","confianza":"alta"}}

Pregunta del usuario:
{pregunta}

Devuelve exclusivamente JSON válido con este formato:
{{
  "tools": ["RAGTool"],
  "tipo_consulta_bd": "ninguna",
  "motivo": "motivo breve de la decisión",
  "confianza": "alta"
}}
"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _extraer_json(self, texto: str) -> dict[str, Any]:
        """
        Extrae JSON incluso si el modelo accidentalmente lo envuelve en markdown.
        """
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

    def _validar_decision_clasificador(self, decision: dict[str, Any]) -> dict[str, Any]:
        """
        Valida que el LLM clasificador solo haya elegido opciones permitidas.
        """
        tools = decision.get("tools", [])
        tipo_consulta_bd = decision.get("tipo_consulta_bd", "ninguna")
        motivo = decision.get("motivo", "")
        confianza = decision.get("confianza", "baja")

        if not isinstance(tools, list):
            raise ValueError("El campo tools debe ser una lista.")

        tools_limpias = []

        for tool in tools:
            if tool not in TOOLS_PERMITIDAS:
                raise ValueError(f"Tool no permitida por el clasificador: {tool}")

            if tool not in tools_limpias:
                tools_limpias.append(tool)

        if not tools_limpias:
            tools_limpias = ["RAGTool"]

        if tipo_consulta_bd not in CONSULTAS_BD_PERMITIDAS:
            raise ValueError(
                f"Consulta BD no permitida por el clasificador: {tipo_consulta_bd}"
            )

        if "DatabaseTool" not in tools_limpias:
            tipo_consulta_bd = "ninguna"

        if "DatabaseTool" in tools_limpias and tipo_consulta_bd == "ninguna":
            raise ValueError(
                "El clasificador pidió DatabaseTool pero no indicó consulta BD válida."
            )

        if confianza not in CONFIANZAS_PERMITIDAS:
            confianza = "baja"

        return {
            "tools": tools_limpias,
            "tipo_consulta_bd": tipo_consulta_bd,
            "motivo": str(motivo).strip(),
            "confianza": confianza,
        }

    def _construir_contexto_rag(self, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "No se recuperó contexto documental del RAG."

        partes = []

        for chunk in chunks:
            partes.append(
                "\n".join(
                    [
                        f"Documento: {chunk['source_file']}",
                        f"Chunk: {chunk['chunk_id']}",
                        "Texto:",
                        chunk["text"],
                    ]
                )
            )

        return "\n\n---\n\n".join(partes)

    def _construir_contexto_bd(self, resultado_bd: dict[str, Any]) -> str:
        if not resultado_bd:
            return "No se recuperaron datos estructurados de la base de datos."

        return "\n".join(
            f"{campo}: {valor}" for campo, valor in resultado_bd.items()
        )

    def _crear_mensajes_respuesta_final(
        self,
        pregunta: str,
        contexto_rag: str,
        contexto_bd: str,
        herramientas: list[str],
    ) -> list[dict[str, str]]:
        system_prompt = (
            "Eres un asistente interno de BANCOMEX especializado en procesos operativos. "
            f"Tu agente asignado es {self.proceso.agente}. "
            f"Solo debes responder sobre el proceso {self.proceso.proceso_id}: {self.proceso.nombre}. "
            "Usa únicamente el contexto proporcionado por RAG y/o base de datos. "
            "No inventes áreas, tiempos, canales, criticidad, pasos, políticas ni responsables. "
            "Si la información no está disponible en el contexto, indícalo claramente. "
            "Responde en español, de forma profesional y clara."
            "No inventes áreas, tiempos, canales, criticidad, pasos, políticas ni responsables. "
            "No agregues recomendaciones genéricas como contactar a un ejecutivo, proporcionar más detalles "
            "o acudir a un área, salvo que esa instrucción aparezca en el contexto recuperado. "
            "Si la información no está disponible en el contexto, indícalo claramente. "
        )

        user_prompt = (
            f"Pregunta del usuario:\n{pregunta}\n\n"
            f"Herramientas usadas: {', '.join(herramientas)}\n\n"
            f"Contexto documental RAG:\n{contexto_rag or 'No se usó RAG.'}\n\n"
            f"Datos estructurados de BD:\n{contexto_bd or 'No se usó BD.'}\n\n"
            "Redacta una respuesta útil para el usuario. "
            "No menciones detalles técnicos internos como embeddings, distancia, chunk index o top-k. "
            "Si usas datos estructurados, responde solo los datos necesarios para la pregunta."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]