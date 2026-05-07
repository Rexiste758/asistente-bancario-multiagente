from app.agentes.agente_especializado_base import AgenteEspecializadoBase
from app.agentes.catalogo_procesos import obtener_proceso


def _obtener_proceso_requerido(proceso_id: str):
    proceso = obtener_proceso(proceso_id)

    if proceso is None:
        raise ValueError(f"No existe configuración para el proceso {proceso_id}.")

    return proceso


class AgenteAclaraciones(AgenteEspecializadoBase):
    """
    Agente especializado en el proceso A:
    Atención de aclaraciones bancarias.
    """

    def __init__(self) -> None:
        super().__init__(_obtener_proceso_requerido("A"))


class AgenteCancelacion(AgenteEspecializadoBase):
    """
    Agente especializado en el proceso B:
    Cancelación de productos financieros.
    """

    def __init__(self) -> None:
        super().__init__(_obtener_proceso_requerido("B"))


class AgenteIncidencias(AgenteEspecializadoBase):
    """
    Agente especializado en el proceso C:
    Escalamiento de incidencias operativas.
    """

    def __init__(self) -> None:
        super().__init__(_obtener_proceso_requerido("C"))


class AgenteDatosCliente(AgenteEspecializadoBase):
    """
    Agente especializado en el proceso D:
    Actualización de datos del cliente.
    """

    def __init__(self) -> None:
        super().__init__(_obtener_proceso_requerido("D"))


class AgenteQuejas(AgenteEspecializadoBase):
    """
    Agente especializado en el proceso E:
    Gestión de quejas internas.
    """

    def __init__(self) -> None:
        super().__init__(_obtener_proceso_requerido("E"))


AGENTES_POR_PROCESO = {
    "A": AgenteAclaraciones,
    "B": AgenteCancelacion,
    "C": AgenteIncidencias,
    "D": AgenteDatosCliente,
    "E": AgenteQuejas,
}


def crear_agente_por_proceso(proceso_id: str) -> AgenteEspecializadoBase:
    """
    Crea el agente concreto correspondiente al proceso indicado.
    """
    proceso_normalizado = proceso_id.strip().upper()
    clase_agente = AGENTES_POR_PROCESO.get(proceso_normalizado)

    if clase_agente is None:
        raise ValueError(f"No existe agente especializado para el proceso {proceso_id}.")

    return clase_agente()