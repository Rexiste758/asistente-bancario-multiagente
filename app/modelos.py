from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class MensajeUsuario(BaseModel):
    """
    Representa el mensaje que escribe el usuario.
    """

    text: str = Field(min_length=1)


class MetadatosSolicitud(BaseModel):
    """
    Guarda información adicional sobre el canal por donde llega la solicitud.

    Para efectos de la prueba. el canal será `cli`, pero dejamos la estructura lista
    para que el mismo flujo pudiera reutilizarse en API REST si hiciera falta.
    """

    channel: str = "cli"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SolicitudAgente(BaseModel):
    """
    Body interno que recibe el orquestador.

    Convertimos cada entrada a una solicitud estructurada con:
    - conversation_id: identifica la conversación activa.
    - user_id: identifica al usuario que envía el mensaje.
    - message: contiene el texto del usuario.
    - metadata: contiene canal y fecha/hora de la solicitud.
    """

    conversation_id: str
    user_id: str
    message: MensajeUsuario
    metadata: MetadatosSolicitud


class FuenteTrazabilidad(BaseModel):
    """
    Describe la evidencia usada para construir la respuesta.

    Puede representar:
    - un chunk recuperado del RAG,
    - una consulta ejecutada en la BD,
    - una respuesta de orientación del orquestador,
    - o una llamada al LLM.

    El campo `details` es flexible porque cada fuente tiene datos distintos.
    """

    type: Literal["rag", "database", "orchestrator", "llm"]
    details: dict[str, Any]


class RespuestaAgente(BaseModel):
    """
    Respuesta estructurada que devuelve el sistema.

    La CLI mostrará principalmente `answer`, pero los demás campos sirven
    para logs y trazabilidad:
    - qué proceso se detectó,
    - qué agente respondió,
    - qué herramientas se usaron,
    - y qué fuentes respaldan la respuesta.
    """

    conversation_id: str
    answer: str
    process_id: str | None = None
    process_name: str | None = None
    agent_used: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    sources: list[FuenteTrazabilidad] = Field(default_factory=list)