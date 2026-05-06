from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MensajeMemoria:
    """
    Representa un mensaje guardado durante la conversación activa.
    No se guarda en disco. Solo vive mientras la aplicación está corriendo.
    """

    rol: str
    contenido: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class EstadoConversacion:
    """
    Guarda el contexto que el orquestador necesita recordar.

    El objetivo no es guardar todo para siempre, sino conservar contexto útil
    dentro de una conversación activa.
    """

    conversation_id: str
    ultimo_proceso_id: str | None = None
    ultimo_proceso_nombre: str | None = None
    ultima_herramienta_usada: str | None = None
    historial: list[MensajeMemoria] = field(default_factory=list)


class MemoriaConversacional:
    """
    Esta implementación funciona con que si la app se reinicia, la memoria se pierde.
    """

    def __init__(self, max_mensajes_por_conversacion: int = 10) -> None:
        self.max_mensajes = max_mensajes_por_conversacion
        self._conversaciones: dict[str, EstadoConversacion] = {}

    def obtener_o_crear(self, conversation_id: str) -> EstadoConversacion:
        if conversation_id not in self._conversaciones:
            self._conversaciones[conversation_id] = EstadoConversacion(
                conversation_id=conversation_id
            )

        return self._conversaciones[conversation_id]

    def agregar_mensaje(
        self,
        conversation_id: str,
        rol: str,
        contenido: str,
    ) -> None:
        """
        Guarda un mensaje dentro del historial corto de la conversación.
        """
        estado = self.obtener_o_crear(conversation_id)
        estado.historial.append(MensajeMemoria(rol=rol, contenido=contenido))

        if len(estado.historial) > self.max_mensajes:
            estado.historial = estado.historial[-self.max_mensajes :]

    def actualizar_proceso(
        self,
        conversation_id: str,
        proceso_id: str | None,
        proceso_nombre: str | None,
    ) -> None:
        """
        Guarda el último proceso detectado por el orquestador.

        Esto permite resolver preguntas de seguimiento como:
        "¿y cuánto tarda?"
        """
        estado = self.obtener_o_crear(conversation_id)
        estado.ultimo_proceso_id = proceso_id
        estado.ultimo_proceso_nombre = proceso_nombre

    def actualizar_herramienta(
        self,
        conversation_id: str,
        herramienta: str | None,
    ) -> None:
        estado = self.obtener_o_crear(conversation_id)
        estado.ultima_herramienta_usada = herramienta

    def obtener_resumen(self, conversation_id: str) -> dict:
        """
        Devuelve una vista simple del estado conversacional.
        """
        estado = self.obtener_o_crear(conversation_id)

        return {
            "conversation_id": estado.conversation_id,
            "ultimo_proceso_id": estado.ultimo_proceso_id,
            "ultimo_proceso_nombre": estado.ultimo_proceso_nombre,
            "ultima_herramienta_usada": estado.ultima_herramienta_usada,
            "mensajes_en_memoria": len(estado.historial),
            "historial": [
                {
                    "rol": mensaje.rol,
                    "contenido": mensaje.contenido,
                    "timestamp": mensaje.timestamp,
                }
                for mensaje in estado.historial
            ],
        }


memoria_conversacional = MemoriaConversacional()