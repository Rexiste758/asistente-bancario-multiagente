import logging
from typing import Any

from openai import OpenAI

from app.configuracion import configuracion

logger = logging.getLogger(__name__)


class ClienteLLM:
    """
    Cliente para interactuar con el modelo LLM configurado.

    Usamos DeepSeek con formato compatible con OpenAI.
    La API key se lee desde .env y nunca se imprime en consola ni en logs.
    """

    def __init__(self) -> None:
        if configuracion.proveedor_llm != "deepseek":
            raise ValueError(
                f"Proveedor LLM no soportado en esta versión: {configuracion.proveedor_llm}"
            )

        if not configuracion.api_key_configurada:
            raise ValueError(
                "Falta DEEPSEEK_API_KEY en el archivo .env. "
                "Configura la variable antes de llamar al LLM."
            )

        self.modelo = configuracion.deepseek_modelo
        self.base_url = configuracion.deepseek_base_url
        self.thinking = configuracion.deepseek_thinking

        self.cliente = OpenAI(
            api_key=configuracion.deepseek_api_key,
            base_url=self.base_url,
        )

    def generar_respuesta(
        self,
        mensajes: list[dict[str, str]],
        temperatura: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Genera una respuesta usando el LLM.

        mensajes:
            Lista de mensajes con formato OpenAI:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        temperatura:
            Controla qué tan variable puede ser la respuesta.
            Usamos valores bajos para reducir respuestas inventadas.

        max_tokens:
            Límite de tokens de salida.
        """
        temperatura_final = (
            configuracion.temperatura_llm
            if temperatura is None
            else temperatura
        )
        max_tokens_final = (
            configuracion.max_tokens_llm
            if max_tokens is None
            else max_tokens
        )

        logger.info(
            "ClienteLLM enviando solicitud | proveedor=%s | modelo=%s | thinking=%s",
            configuracion.proveedor_llm,
            self.modelo,
            self.thinking,
        )

        respuesta = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=mensajes,
            temperature=temperatura_final,
            max_tokens=max_tokens_final,
            extra_body={
                "thinking": {
                    "type": self.thinking
                }
            },
        )

        contenido = respuesta.choices[0].message.content or ""

        return {
            "respuesta": contenido.strip(),
            "trazabilidad": {
                "type": "llm",
                "details": {
                    "provider": configuracion.proveedor_llm,
                    "model": self.modelo,
                    "base_url": self.base_url,
                    "thinking": self.thinking,
                    "temperature": temperatura_final,
                    "max_tokens": max_tokens_final,
                    "api_key": "configurada_no_expuesta",
                },
            },
        }