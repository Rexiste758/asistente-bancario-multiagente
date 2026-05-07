import logging
import sqlite3
from pathlib import Path

from rich.console import Console
from rich.table import Table

from app.configuracion import configuracion, preparar_carpetas_runtime
from app.registro import configurar_logs

logger = logging.getLogger(__name__)
consola = Console()

RUTA_BASE_DATOS = Path(__file__).resolve().parent
RUTA_ESQUEMA = RUTA_BASE_DATOS / "esquema.sql"
RUTA_DATOS_INICIALES = RUTA_BASE_DATOS / "datos_iniciales.sql"


def leer_archivo_sql(ruta_archivo: Path) -> str:
    """
    Lee un archivo SQL desde disco.

    Esto mantiene separada la estructura de la BD de los datos iniciales,
    para que sea fácil revisar qué tabla se crea y qué información se carga.
    """
    return ruta_archivo.read_text(encoding="utf-8")


def inicializar_base_datos() -> None:
    """
    Crea la base SQLite con los cinco procesos operativos A-E.

    El script es reproducible: si se ejecuta varias veces,
    vuelve a crear la tabla desde cero y carga nuevamente los datos.
    """
    preparar_carpetas_runtime()
    configurar_logs()

    ruta_sqlite = configuracion.path_sqlite

    logger.info("Inicializando base de datos SQLite en: %s", ruta_sqlite)

    esquema_sql = leer_archivo_sql(RUTA_ESQUEMA)
    datos_sql = leer_archivo_sql(RUTA_DATOS_INICIALES)

    with sqlite3.connect(ruta_sqlite) as conexion:
        conexion.executescript(esquema_sql)
        conexion.executescript(datos_sql)
        conexion.commit()

        cursor = conexion.execute(
            """
            SELECT proceso_id,nombre_proceso,area_responsable,tiempo_promedio_resolucion,canal_atencion,nivel_criticidad
            FROM procesos_operativos
            ORDER BY proceso_id
            """
        )

        registros = cursor.fetchall()

    logger.info("Base de datos inicializada. Registros cargados: %s", len(registros))

    tabla = Table(title="Procesos operativos cargados en SQLite")
    tabla.add_column("Código", style="bold")
    tabla.add_column("Proceso")
    tabla.add_column("Área responsable")
    tabla.add_column("Tiempo")
    tabla.add_column("Canal")
    tabla.add_column("Criticidad")

    for registro in registros:
        tabla.add_row(*[str(valor) for valor in registro])

    consola.print(tabla)
    consola.print(f"[green]Base creada correctamente:[/green] {ruta_sqlite}")


if __name__ == "__main__":
    inicializar_base_datos()