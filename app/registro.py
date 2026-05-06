import logging
from pathlib import Path

from app.configuracion import configuracion


def configurar_logs() -> None:
    """
    Configuración de logs en consola y archivo.

    El archivo app/logs/app.log deja evidencia de la trazabilidad.
    """
    Path("app/logs").mkdir(parents=True, exist_ok=True)

    logger_principal = logging.getLogger()

    if logger_principal.handlers:
        return

    nivel = getattr(logging, configuracion.nivel_logs.upper(), logging.INFO)
    logger_principal.setLevel(nivel)

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    salida_consola = logging.StreamHandler()
    salida_consola.setLevel(nivel)
    salida_consola.setFormatter(formato)

    salida_archivo = logging.FileHandler("app/logs/app.log", encoding="utf-8")
    salida_archivo.setLevel(nivel)
    salida_archivo.setFormatter(formato)

    logger_principal.addHandler(salida_consola)
    logger_principal.addHandler(salida_archivo)