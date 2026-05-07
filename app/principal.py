import json
import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.configuracion import configuracion, preparar_carpetas_runtime
from app.herramientas.herramienta_bd import HerramientaBD
from app.llm.cliente_llm import ClienteLLM
from app.agentes.catalogo_procesos import detectar_proceso_por_texto, listar_catalogo
from app.memoria.memoria_conversacional import memoria_conversacional
from app.modelos import MetadatosSolicitud, MensajeUsuario, SolicitudAgente
from app.registro import configurar_logs

cli = typer.Typer(help="CLI del asistente multiagente para procesos internos bancarios.")
consola = Console()
logger = logging.getLogger(__name__)


@cli.command()
def health() -> None:
    """
    Revisa que la configuración base del proyecto esté cargando correctamente.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    logger.info("Ejecutando validación health del proyecto.")

    tabla = Table(title="Estado del proyecto")
    tabla.add_column("Elemento", style="bold")
    tabla.add_column("Valor")

    tabla.add_row("Ambiente", configuracion.ambiente_app)
    tabla.add_row("Proveedor LLM", configuracion.proveedor_llm)
    tabla.add_row("DeepSeek Base URL", configuracion.deepseek_base_url)
    tabla.add_row("Modelo DeepSeek", configuracion.deepseek_modelo)
    tabla.add_row("Thinking Mode", configuracion.deepseek_thinking)
    tabla.add_row(
        "API key DeepSeek",
        "configurada" if configuracion.api_key_configurada else "no configurada",
    )
    tabla.add_row("Ruta SQLite", configuracion.ruta_sqlite)
    tabla.add_row("Ruta Chroma", configuracion.ruta_chroma)
    tabla.add_row("Colección RAG", configuracion.nombre_coleccion_rag)
    tabla.add_row("Chunk size", str(configuracion.tamano_chunk))
    tabla.add_row("Chunk overlap", str(configuracion.overlap_chunk))
    tabla.add_row("Top K", str(configuracion.top_k_rag))
    tabla.add_row("Modelo embeddings", configuracion.modelo_embeddings)
    tabla.add_row("Dimensión embeddings", str(configuracion.dimension_embeddings))

    consola.print(tabla)
    consola.print(
        Panel.fit(
            "Validación completada. La API key no se imprime por seguridad.",
            title="OK",
        )
    )


@cli.command("preview-request")
def preview_request(
    mensaje: str = typer.Argument(..., help="Mensaje que escribiría el usuario."),
    conversation_id: str = typer.Option("demo-001", help="ID de conversación."),
    user_id: str = typer.Option("usuario_cli", help="ID del usuario."),
) -> None:
    """
    Muestra el body interno que la CLI enviará al orquestador.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    solicitud = SolicitudAgente(
        conversation_id=conversation_id,
        user_id=user_id,
        message=MensajeUsuario(text=mensaje),
        metadata=MetadatosSolicitud(channel="cli"),
    )

    logger.info(
        "SolicitudAgente creada | conversation_id=%s | user_id=%s | channel=%s",
        solicitud.conversation_id,
        solicitud.user_id,
        solicitud.metadata.channel,
    )

    consola.print_json(json.dumps(solicitud.model_dump(), ensure_ascii=False))


@cli.command("listar-procesos")
def listar_procesos() -> None:
    """
    Lista los procesos operativos disponibles en la base estructurada.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    herramienta_bd = HerramientaBD()
    respuesta = herramienta_bd.listar_procesos()

    tabla = Table(title="Procesos disponibles")
    tabla.add_column("Código", style="bold")
    tabla.add_column("Proceso")

    for proceso in respuesta["resultado"]:
        tabla.add_row(proceso["proceso_id"], proceso["nombre_proceso"])

    consola.print(tabla)

    consola.print("\n[bold]Trazabilidad BD:[/bold]")
    consola.print_json(
        json.dumps(respuesta["trazabilidad"], ensure_ascii=False)
    )


@cli.command("probar-bd")
def probar_bd(
    proceso_id: str = typer.Argument(..., help="Código del proceso: A, B, C, D o E."),
    tipo_consulta: str = typer.Argument(
        "resumen_operativo",
        help=(
            "Consulta permitida: nombre_proceso, area_responsable, "
            "tiempo_promedio_resolucion, canal_atencion, "
            "nivel_criticidad o resumen_operativo."
        ),
    ),
) -> None:
    """
    Prueba una consulta estructurada usando queries predefinidas.

    Este comando valida que la BD responde solo con los campos solicitados,
    sin que el LLM genere SQL.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    herramienta_bd = HerramientaBD()
    respuesta = herramienta_bd.consultar_proceso(proceso_id, tipo_consulta)

    consola.print("[bold green]Resultado BD:[/bold green]")
    consola.print_json(
        json.dumps(respuesta["resultado"], ensure_ascii=False)
    )

    consola.print("\n[bold]Trazabilidad BD:[/bold]")
    consola.print_json(
        json.dumps(respuesta["trazabilidad"], ensure_ascii=False)
    )


@cli.command("probar-rag")
def probar_rag(
    proceso_id: str = typer.Argument(..., help="Código del proceso: A, B, C, D o E."),
    pregunta: str = typer.Argument(..., help="Pregunta para buscar en documentos RAG."),
) -> None:
    """
    Prueba la recuperación documental desde ChromaDB.

    Este comando valida que el RAG recupere chunks filtrando por proceso
    y que devuelva evidencia textual para trazabilidad.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    from app.herramientas.herramienta_rag import HerramientaRAG

    herramienta_rag = HerramientaRAG()
    respuesta = herramienta_rag.buscar(
        pregunta=pregunta,
        process_id=proceso_id,
    )

    consola.print("[bold green]Chunks recuperados:[/bold green]")

    for chunk in respuesta["chunks"]:
        consola.print(
            Panel(
                (
                    f"[bold]Chunk:[/bold] {chunk['chunk_id']}\n"
                    f"[bold]Documento:[/bold] {chunk['source_file']}\n"
                    f"[bold]Índice:[/bold] {chunk['chunk_index']}\n"
                    f"[bold]Distancia:[/bold] {chunk['distance']}\n\n"
                    f"{chunk['text_preview']}"
                ),
                title=f"Proceso {chunk['process_id']} - {chunk['process_name']}",
            )
        )

    consola.print("\n[bold]Trazabilidad RAG:[/bold]")
    consola.print_json(
        json.dumps(respuesta["trazabilidad"], ensure_ascii=False)
    )


@cli.command("probar-llm")
def probar_llm(
    pregunta: str = typer.Argument(
        "¿Qué puedes hacer?",
        help="Pregunta de prueba para validar conexión con el LLM.",
    ),
) -> None:
    """
    Prueba la conexión con DeepSeek.

    Este comando valida que la API key, el modelo, el thinking mode
    y los parámetros del LLM estén funcionando desde Docker.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    cliente_llm = ClienteLLM()

    mensajes = [
        {
            "role": "system",
            "content": (
                "Eres un asistente interno de BANCOMEX. "
                "Responde en español, de forma breve y profesional. "
                "No inventes información operativa; esta prueba solo valida "
                "que el modelo pueda redactar una respuesta natural."
            ),
        },
        {
            "role": "user",
            "content": pregunta,
        },
    ]

    respuesta = cliente_llm.generar_respuesta(mensajes)

    consola.print(
        Panel(
            respuesta["respuesta"],
            title="Respuesta LLM",
        )
    )

    consola.print("\n[bold]Trazabilidad LLM:[/bold]")
    consola.print_json(
        json.dumps(respuesta["trazabilidad"], ensure_ascii=False)
    )


@cli.command("probar-memoria")
def probar_memoria(
    conversation_id: str = typer.Option("demo-001", help="ID de conversación."),
) -> None:
    """
    Prueba la memoria conversacional en una conversación activa.

    Simula dos turnos para validar que el sistema conserva el último proceso.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    memoria_conversacional.agregar_mensaje(
        conversation_id=conversation_id,
        rol="usuario",
        contenido="Explícame el proceso de aclaraciones.",
    )
    memoria_conversacional.actualizar_proceso(
        conversation_id=conversation_id,
        proceso_id="A",
        proceso_nombre="Atención de aclaraciones bancarias",
    )
    memoria_conversacional.actualizar_herramienta(
        conversation_id=conversation_id,
        herramienta="RAG",
    )

    memoria_conversacional.agregar_mensaje(
        conversation_id=conversation_id,
        rol="usuario",
        contenido="¿Y cuánto tarda?",
    )

    resumen = memoria_conversacional.obtener_resumen(conversation_id)

    consola.print("[bold green]Estado de memoria conversacional:[/bold green]")
    consola.print_json(json.dumps(resumen, ensure_ascii=False))


@cli.command("probar-catalogo")
def probar_catalogo(
    mensaje: str = typer.Argument(
        ...,
        help="Mensaje para probar detección de proceso.",
    ),
) -> None:
    """
    Prueba la detección inicial de proceso usando el catálogo operativo.

    Esta prueba permite ver por qué el sistema cree que una pregunta
    corresponde a un proceso A-E.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    deteccion = detectar_proceso_por_texto(mensaje)

    consola.print("[bold green]Resultado de detección:[/bold green]")
    consola.print_json(json.dumps(deteccion, ensure_ascii=False))

    tabla = Table(title="Procesos disponibles en catálogo")
    tabla.add_column("Código", style="bold")
    tabla.add_column("Proceso")
    tabla.add_column("Agente")

    for proceso in listar_catalogo():
        tabla.add_row(proceso.proceso_id, proceso.nombre, proceso.agente)

    consola.print(tabla)

if __name__ == "__main__":
    cli()