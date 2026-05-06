import logging
import os
from pathlib import Path
from typing import Any

# Se configura antes de crear clientes de ChromaDB.
# Esto ayuda a evitar telemetría anónima durante la demo.
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings
from docx import Document
from rich.console import Console
from rich.table import Table
from sentence_transformers import SentenceTransformer

from app.configuracion import configuracion, preparar_carpetas_runtime
from app.registro import configurar_logs

logger = logging.getLogger(__name__)
consola = Console()

CARPETA_DOCUMENTOS = Path("app/documentos")

# Relación entre documentos Word y procesos del RAG.
# Estos datos no viven en la BD porque son parte de la configuración documental del RAG.
# La BD sigue siendo la fuente para área, tiempo, canal y criticidad.

CATALOGO_DOCUMENTOS = {
    "A_aclaraciones_bancarias.docx": {
        "process_id": "A",
        "process_name": "Atención de aclaraciones bancarias",
    },
    "B_cancelacion_productos.docx": {
        "process_id": "B",
        "process_name": "Cancelación de productos financieros",
    },
    "C_escalamiento_incidencias.docx": {
        "process_id": "C",
        "process_name": "Escalamiento de incidencias operativas",
    },
    "D_actualizacion_datos_cliente.docx": {
        "process_id": "D",
        "process_name": "Actualización de datos del cliente",
    },
    "E_quejas_internas.docx": {
        "process_id": "E",
        "process_name": "Gestión de quejas internas",
    },
}

# Parámetros expuestos para cumplir el requisito del RAG.

CHUNK_SIZE = configuracion.tamano_chunk
CHUNK_OVERLAP = configuracion.overlap_chunk
EMBEDDING_MODEL = configuracion.modelo_embeddings
EMBEDDING_DIMENSION = configuracion.dimension_embeddings
TOP_K = configuracion.top_k_rag
SEARCH_STRATEGY = "similarity"
VECTOR_STORE = "ChromaDB"


def silenciar_telemetria_chroma() -> None:
    """
    Silencia mensajes internos de telemetría de ChromaDB.
    """
    os.environ["ANONYMIZED_TELEMETRY"] = "False"

    loggers_a_silenciar = [
        "chromadb.telemetry",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.posthog",
        "posthog",
    ]

    for nombre_logger in loggers_a_silenciar:
        logger_ruidoso = logging.getLogger(nombre_logger)
        logger_ruidoso.disabled = True
        logger_ruidoso.propagate = False
        logger_ruidoso.setLevel(logging.CRITICAL)


def leer_docx(ruta_documento: Path) -> str:
    """
    Extrae texto de un documento Word.

    Los documentos fuente son solo texto, por eso se leen por párrafos y se descartan líneas vacías.
    """
    documento = Document(ruta_documento)
    parrafos = []

    for parrafo in documento.paragraphs:
        texto = parrafo.text.strip()
        if texto:
            parrafos.append(texto)

    return "\n".join(parrafos)


def dividir_en_chunks(texto: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Divide texto largo en fragmentos con traslape.

    El traslape ayuda a conservar contexto cuando una idea queda entre el final de un fragmento y el inicio del siguiente.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("RAG_CHUNK_OVERLAP debe ser menor que RAG_CHUNK_SIZE.")

    chunks = []
    inicio = 0
    longitud = len(texto)

    while inicio < longitud:
        fin = min(inicio + chunk_size, longitud)
        chunk = texto[inicio:fin].strip()

        if chunk:
            chunks.append(chunk)

        if fin == longitud:
            break

        inicio = fin - chunk_overlap

    return chunks


def reiniciar_coleccion(cliente: Any):
    """
    Reinicia la colección para que la ingesta sea reproducible.

    Si el script se ejecuta varias veces, se elimina la colección anterior y se vuelve a construir desde los documentos Word actuales.
    """
    nombre = configuracion.nombre_coleccion_rag

    try:
        cliente.delete_collection(name=nombre)
        logger.info("Colección Chroma eliminada para reconstrucción: %s", nombre)
    except Exception:
        logger.info("No existía colección previa en Chroma: %s", nombre)

    return cliente.get_or_create_collection(
        name=nombre,
        metadata={
            "hnsw:space": "cosine",
            "search_strategy": SEARCH_STRATEGY,
            "vector_store": VECTOR_STORE,
        },
    )


def preparar_chunks() -> list[dict[str, Any]]:
    """
    Lee los documentos configurados y genera chunks con metadata.

    Cada chunk conserva el código de proceso para que la búsqueda RAG pueda filtrarse por agente especializado.
    """
    registros = []

    for nombre_archivo, datos in CATALOGO_DOCUMENTOS.items():
        ruta_documento = CARPETA_DOCUMENTOS / nombre_archivo

        if not ruta_documento.exists():
            raise FileNotFoundError(f"No existe el documento requerido: {ruta_documento}")

        texto = leer_docx(ruta_documento)
        chunks = dividir_en_chunks(texto, CHUNK_SIZE, CHUNK_OVERLAP)

        logger.info(
            "Documento procesado | archivo=%s | proceso=%s | chunks=%s",
            nombre_archivo,
            datos["process_id"],
            len(chunks),
        )

        for indice, chunk in enumerate(chunks, start=1):
            chunk_id = f"{datos['process_id']}_{indice:03d}"

            registros.append(
                {
                    "id": chunk_id,
                    "texto": chunk,
                    "metadata": {
                        "process_id": datos["process_id"],
                        "process_name": datos["process_name"],
                        "source_file": nombre_archivo,
                        "chunk_index": indice,
                    },
                }
            )

    return registros


def ejecutar_ingesta() -> None:
    """
    Ejecuta el pipeline reproducible del RAG.

    Flujo:
    carga de documentos -> chunking -> embeddings -> almacenamiento en ChromaDB.
    """
    preparar_carpetas_runtime()
    configurar_logs()
    silenciar_telemetria_chroma()

    logger.info("Iniciando pipeline de ingesta RAG.")

    registros = preparar_chunks()

    if not registros:
        raise ValueError("No se generaron chunks para ingestar.")

    logger.info("Cargando modelo de embeddings: %s", EMBEDDING_MODEL)
    modelo_embeddings = SentenceTransformer(EMBEDDING_MODEL)

    textos = [registro["texto"] for registro in registros]
    ids = [registro["id"] for registro in registros]
    metadatas = [registro["metadata"] for registro in registros]

    embeddings = modelo_embeddings.encode(
        textos,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    dimension_real = len(embeddings[0]) if embeddings else 0

    if dimension_real != EMBEDDING_DIMENSION:
        raise ValueError(
            f"La dimensión real del embedding es {dimension_real}, "
            f"pero se configuró {EMBEDDING_DIMENSION}."
        )

    cliente = chromadb.PersistentClient(
        path=str(configuracion.path_chroma),
        settings=Settings(anonymized_telemetry=False),
    )

    coleccion = reiniciar_coleccion(cliente)

    coleccion.add(
        ids=ids,
        documents=textos,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    total = coleccion.count()

    logger.info(
        "Ingesta RAG completada | vector_store=%s | coleccion=%s | chunks=%s",
        VECTOR_STORE,
        configuracion.nombre_coleccion_rag,
        total,
    )

    tabla = Table(title="Resumen de ingesta RAG")
    tabla.add_column("Parámetro", style="bold")
    tabla.add_column("Valor")

    tabla.add_row("Vector store", VECTOR_STORE)
    tabla.add_row("Colección", configuracion.nombre_coleccion_rag)
    tabla.add_row("Estrategia de búsqueda", SEARCH_STRATEGY)
    tabla.add_row("Chunk size", str(CHUNK_SIZE))
    tabla.add_row("Chunk overlap", str(CHUNK_OVERLAP))
    tabla.add_row("Top K", str(TOP_K))
    tabla.add_row("Modelo embeddings", EMBEDDING_MODEL)
    tabla.add_row("Dimensión embeddings", str(EMBEDDING_DIMENSION))
    tabla.add_row("Chunks almacenados", str(total))
    tabla.add_row("Ruta Chroma", str(configuracion.path_chroma))

    consola.print(tabla)
    consola.print("[green]Pipeline de ingesta RAG completado correctamente.[/green]")


if __name__ == "__main__":
    ejecutar_ingesta()