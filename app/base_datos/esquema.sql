-- Tabla principal de procesos operativos internos del banco.
-- Cada registro corresponde a un proceso documentado en el RAG.

DROP TABLE IF EXISTS procesos_operativos;

CREATE TABLE procesos_operativos (
    proceso_id TEXT PRIMARY KEY,
    nombre_proceso TEXT NOT NULL,
    area_responsable TEXT NOT NULL,
    tiempo_promedio_resolucion TEXT NOT NULL,
    canal_atencion TEXT NOT NULL,
    nivel_criticidad TEXT NOT NULL
);