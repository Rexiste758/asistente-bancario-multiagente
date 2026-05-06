from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """
    Configuración central del proyecto.

    Los valores vienen del archivo .env. Esto evita dejar API keys,
    rutas o parámetros escritos directamente en el código.
    """

    ambiente_app: str = Field(default="local", validation_alias="APP_ENV")
    nivel_logs: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    proveedor_llm: Literal["deepseek", "openai", "ollama"] = Field(
        default="deepseek",
        validation_alias="LLM_PROVIDER",
    )

    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        validation_alias="DEEPSEEK_BASE_URL",
    )
    deepseek_modelo: str = Field(
        default="deepseek-v4-flash",
        validation_alias="DEEPSEEK_MODEL",
    )
    deepseek_thinking: Literal["enabled", "disabled"] = Field(
        default="disabled",
        validation_alias="DEEPSEEK_THINKING",
    )

    temperatura_llm: float = Field(default=0.1, validation_alias="LLM_TEMPERATURE")
    max_tokens_llm: int = Field(default=700, validation_alias="LLM_MAX_TOKENS")

    ruta_sqlite: str = Field(
        default="data/sqlite/bank_processes.db",
        validation_alias="SQLITE_DB_PATH",
    )

    ruta_chroma: str = Field(default="data/chroma", validation_alias="CHROMA_PATH")
    nombre_coleccion_rag: str = Field(
        default="bank_processes",
        validation_alias="RAG_COLLECTION_NAME",
    )
    tamano_chunk: int = Field(default=700, validation_alias="RAG_CHUNK_SIZE")
    overlap_chunk: int = Field(default=120, validation_alias="RAG_CHUNK_OVERLAP")
    top_k_rag: int = Field(default=3, validation_alias="RAG_TOP_K")

    modelo_embeddings: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        validation_alias="EMBEDDING_MODEL",
    )
    dimension_embeddings: int = Field(
        default=384,
        validation_alias="EMBEDDING_DIMENSION",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def api_key_configurada(self) -> bool:
        return bool(self.deepseek_api_key.strip())

    @property
    def path_sqlite(self) -> Path:
        return Path(self.ruta_sqlite)

    @property
    def path_chroma(self) -> Path:
        return Path(self.ruta_chroma)


configuracion = Configuracion()


def preparar_carpetas_runtime() -> None:
    """
    Crea carpetas que la aplicación necesita al ejecutarse.

    No crea la base de datos ni el vector store todavía, solo garantiza que las rutas existan.
    """
    Path("app/logs").mkdir(parents=True, exist_ok=True)
    configuracion.path_sqlite.parent.mkdir(parents=True, exist_ok=True)
    configuracion.path_chroma.mkdir(parents=True, exist_ok=True)