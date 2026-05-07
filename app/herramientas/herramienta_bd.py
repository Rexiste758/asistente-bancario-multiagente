import logging
import sqlite3
from pathlib import Path
from typing import Any

from app.configuracion import configuracion

logger = logging.getLogger(__name__)


class HerramientaBD:
    """
    Herramienta para consultar la base estructurada de procesos operativos.

    Esta clase no permite SQL libre. Solo ejecuta consultas predefinidas
    para mantener el comportamiento controlado y evitar alucinaciones.
    """

    CONSULTAS_PERMITIDAS: dict[str, dict[str, Any]] = {
        "nombre_proceso": {
            "query_id": "get_nombre_proceso_by_process",
            "sql": """
                SELECT nombre_proceso
                FROM procesos_operativos
                WHERE proceso_id = ?
            """,
            "campos": ["nombre_proceso"],
        },
        "area_responsable": {
            "query_id": "get_area_responsable_by_process",
            "sql": """
                SELECT area_responsable
                FROM procesos_operativos
                WHERE proceso_id = ?
            """,
            "campos": ["area_responsable"],
        },
        "tiempo_promedio_resolucion": {
            "query_id": "get_tiempo_resolucion_by_process",
            "sql": """
                SELECT tiempo_promedio_resolucion
                FROM procesos_operativos
                WHERE proceso_id = ?
            """,
            "campos": ["tiempo_promedio_resolucion"],
        },
        "canal_atencion": {
            "query_id": "get_canal_atencion_by_process",
            "sql": """
                SELECT canal_atencion
                FROM procesos_operativos
                WHERE proceso_id = ?
            """,
            "campos": ["canal_atencion"],
        },
        "nivel_criticidad": {
            "query_id": "get_criticidad_by_process",
            "sql": """
                SELECT nivel_criticidad
                FROM procesos_operativos
                WHERE proceso_id = ?
            """,
            "campos": ["nivel_criticidad"],
        },
        "resumen_operativo": {
            "query_id": "get_resumen_operativo_by_process",
            "sql": """
                SELECT nombre_proceso,
                       area_responsable,
                       tiempo_promedio_resolucion,
                       canal_atencion,
                       nivel_criticidad
                FROM procesos_operativos
                WHERE proceso_id = ?
            """,
            "campos": [
                "nombre_proceso",
                "area_responsable",
                "tiempo_promedio_resolucion",
                "canal_atencion",
                "nivel_criticidad",
            ],
        },
    }

    CONSULTA_LISTAR_PROCESOS = {
        "query_id": "list_procesos_operativos",
        "sql": """
            SELECT proceso_id,
                   nombre_proceso
            FROM procesos_operativos
            ORDER BY proceso_id
        """,
        "campos": ["proceso_id", "nombre_proceso"],
    }

    def __init__(self, ruta_bd: str | Path | None = None) -> None:
        self.ruta_bd = Path(ruta_bd or configuracion.ruta_sqlite)

    def _validar_base_existente(self) -> None:
        """
        Verifica que el archivo SQLite exista antes de consultar.
        """
        if not self.ruta_bd.exists():
            raise FileNotFoundError(
                f"No existe la base SQLite en {self.ruta_bd}. "
                "Ejecuta primero: docker compose run --rm app "
                "python -m app.base_datos.inicializar_bd"
            )

    def consultar_proceso(self, proceso_id: str, tipo_consulta: str) -> dict[str, Any]:
        """
        Consulta un dato estructurado de un proceso.

        proceso_id:
            Código del proceso: A, B, C, D o E.

        tipo_consulta:
            Una de las consultas permitidas, por ejemplo:
            area_responsable, tiempo_promedio_resolucion o resumen_operativo.
        """
        self._validar_base_existente()

        proceso_id_normalizado = proceso_id.strip().upper()
        tipo_normalizado = tipo_consulta.strip().lower()

        if tipo_normalizado not in self.CONSULTAS_PERMITIDAS:
            consultas = ", ".join(self.CONSULTAS_PERMITIDAS.keys())
            raise ValueError(
                f"Consulta BD no permitida: {tipo_consulta}. "
                f"Consultas disponibles: {consultas}"
            )

        definicion = self.CONSULTAS_PERMITIDAS[tipo_normalizado]
        sql = definicion["sql"]
        campos = definicion["campos"]
        parametros = [proceso_id_normalizado]

        logger.info(
            "HerramientaBD ejecutando consulta | query_id=%s | proceso_id=%s | campos=%s",
            definicion["query_id"],
            proceso_id_normalizado,
            campos,
        )

        with sqlite3.connect(self.ruta_bd) as conexion:
            cursor = conexion.execute(sql, parametros)
            fila = cursor.fetchone()

        if fila is None:
            raise ValueError(
                f"No existe registro para proceso_id={proceso_id_normalizado}"
            )

        resultado = dict(zip(campos, fila))

        return {
            "resultado": resultado,
            "trazabilidad": {
                "type": "database",
                "details": {
                    "query_id": definicion["query_id"],
                    "sql": " ".join(sql.split()),
                    "params": parametros,
                    "fields": campos,
                    "table": "procesos_operativos",
                    "process_id": proceso_id_normalizado,
                },
            },
        }

    def listar_procesos(self) -> dict[str, Any]:
        """
        Lista los procesos disponibles en la BD.

        Esto será útil cuando el orquestador necesite orientar al usuario
        sobre qué procesos internos puede consultar.
        """
        self._validar_base_existente()

        definicion = self.CONSULTA_LISTAR_PROCESOS
        sql = definicion["sql"]
        campos = definicion["campos"]

        logger.info(
            "HerramientaBD listando procesos | query_id=%s",
            definicion["query_id"],
        )

        with sqlite3.connect(self.ruta_bd) as conexion:
            cursor = conexion.execute(sql)
            filas = cursor.fetchall()

        procesos = [dict(zip(campos, fila)) for fila in filas]

        return {
            "resultado": procesos,
            "trazabilidad": {
                "type": "database",
                "details": {
                    "query_id": definicion["query_id"],
                    "sql": " ".join(sql.split()),
                    "params": [],
                    "fields": campos,
                    "table": "procesos_operativos",
                },
            },
        }