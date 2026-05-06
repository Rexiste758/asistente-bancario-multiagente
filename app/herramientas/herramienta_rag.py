import logging
import os
from pathlib import Path
from typing import Any

# Se configura antes de crear clientes ChromaDB.
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.configuracion import configuracion

logger = logging.getLogger(__name__)


class HerramientaRAG:
    """
    Herramienta para consultar el vector store documental.

    Esta clase recupera chunks desde ChromaDB usando búsqueda semántica. La búsqueda se filtra por process_id para evitar mezclar información entre procesos distintos.
    """

    SEARCH_STRATEGY = "similarity"
    VECTOR_STORE = "ChromaDB"

    def __init__(self) -> None:
        self.ruta_chroma = Path(configuracion.ruta_chroma)
        self.nombre_coleccion = configuracion.nombre_coleccion_rag
        self.top_k = configuracion.top_k_rag
        self.modelo_embeddings_nombre = configuracion.modelo_embeddings

        self._silenciar_telemetria_chroma()

        self.modelo_embeddings = SentenceTransformer(self.modelo_embeddings_nombre)
        self.cliente = chromadb.PersistentClient(
            path=str(self.ruta_chroma),
            settings=Settings(anonymized_telemetry=False),
        )

    def _silenciar_telemetria_chroma(self) -> None:
        """
        Evita que logs internos de telemetría ensucien la salida de consola.
        """
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

    def _obtener_coleccion(self):
        """
        Obtiene la colección RAG.

        Si no existe, significa que falta ejecutar la ingesta:
        docker compose run --rm app python -m app.rag.ingesta
        """
        try:
            return self.cliente.get_collection(name=self.nombre_coleccion)
        except Exception as error:
            raise RuntimeError(
                f"No existe la colección RAG '{self.nombre_coleccion}'. "
                "Ejecuta primero: docker compose run --rm app python -m app.rag.ingesta"
            ) from error

    def buscar(
        self,
        pregunta: str,
        process_id: str,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """
        Busca fragmentos relevantes para una pregunta dentro de un proceso.

        pregunta:
            Texto del usuario.

        process_id:
            Código del proceso A, B, C, D o E. Se usa como filtro de metadata.

        top_k:
            Número de chunks a recuperar. Si no se envía, usa el valor del .env.
        """
        pregunta_limpia = pregunta.strip()
        proceso_normalizado = process_id.strip().upper()
        limite_resultados = top_k or self.top_k

        if not pregunta_limpia:
            raise ValueError("La pregunta no puede estar vacía.")

        logger.info(
            "HerramientaRAG buscando contexto | proceso=%s | top_k=%s | estrategia=%s",
            proceso_normalizado,
            limite_resultados,
            self.SEARCH_STRATEGY,
        )

        coleccion = self._obtener_coleccion()

        embedding_pregunta = self.modelo_embeddings.encode(
            [pregunta_limpia],
            normalize_embeddings=True,
        ).tolist()

        resultados = coleccion.query(
            query_embeddings=embedding_pregunta,
            n_results=limite_resultados,
            where={"process_id": proceso_normalizado},
            include=["documents", "metadatas", "distances"],
        )

        chunks = self._formatear_resultados(resultados)

        if not chunks:
            logger.warning(
                "HerramientaRAG no encontró chunks | proceso=%s | pregunta=%s",
                proceso_normalizado,
                pregunta_limpia,
            )

        return {
            "chunks": chunks,
            "trazabilidad": {
                "type": "rag",
                "details": {
                    "vector_store": self.VECTOR_STORE,
                    "collection": self.nombre_coleccion,
                    "search_strategy": self.SEARCH_STRATEGY,
                    "embedding_model": self.modelo_embeddings_nombre,
                    "embedding_dimension": configuracion.dimension_embeddings,
                    "chunk_size": configuracion.tamano_chunk,
                    "chunk_overlap": configuracion.overlap_chunk,
                    "top_k": limite_resultados,
                    "process_id": proceso_normalizado,
                    "chunks_found": len(chunks),
                    "sources": [
                        {
                            "chunk_id": chunk["chunk_id"],
                            "source_file": chunk["source_file"],
                            "chunk_index": chunk["chunk_index"],
                            "distance": chunk["distance"],
                            "text_preview": chunk["text_preview"],
                        }
                        for chunk in chunks
                    ],
                },
            },
        }

    def _formatear_resultados(self, resultados: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Convierte la respuesta cruda de ChromaDB en una lista más clara.

        Chroma devuelve listas anidadas porque puede recibir varias consultas
        al mismo tiempo. En este multiagente consultamos una pregunta a la vez.
        """
        documentos = resultados.get("documents", [[]])[0]
        metadatas = resultados.get("metadatas", [[]])[0]
        distances = resultados.get("distances", [[]])[0]
        ids = resultados.get("ids", [[]])[0]

        chunks = []

        for indice, documento in enumerate(documentos):
            metadata = metadatas[indice] or {}
            distance = distances[indice] if indice < len(distances) else None
            chunk_id = ids[indice] if indice < len(ids) else ""

            texto_limpio = " ".join(documento.split())
            vista_previa = texto_limpio[:900]

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": documento,
                    "text_preview": vista_previa,
                    "distance": distance,
                    "process_id": metadata.get("process_id"),
                    "process_name": metadata.get("process_name"),
                    "source_file": metadata.get("source_file"),
                    "chunk_index": metadata.get("chunk_index"),
                }
            )

        return chunks