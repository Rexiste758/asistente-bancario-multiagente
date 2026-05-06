-- Datos para los procesos operativos internos del banco.
-- Cada registro tiene correspondencia con un documento RAG A-E.

INSERT INTO procesos_operativos (
    proceso_id,
    nombre_proceso,
    area_responsable,
    tiempo_promedio_resolucion,
    canal_atencion,
    nivel_criticidad
) VALUES
(
    'A',
    'Atención de aclaraciones bancarias',
    'Centro de Atención y Resolución Bancaria',
    '48 horas hábiles',
    'Portal interno de aclaraciones, sucursal o contact center',
    'Media'
),
(
    'B',
    'Cancelación de productos financieros',
    'Mesa de Operaciones de Productos',
    '72 horas hábiles',
    'Mesa de servicio interna o sucursal',
    'Alta'
),
(
    'C',
    'Escalamiento de incidencias operativas',
    'Coordinación de Soporte Operativo',
    '24 horas hábiles',
    'Mesa de ayuda operativa',
    'Alta'
),
(
    'D',
    'Actualización de datos del cliente',
    'Unidad de Administración de Datos del Cliente',
    '24 a 48 horas hábiles',
    'Portal interno de mantenimiento de clientes',
    'Media'
),
(
    'E',
    'Gestión de quejas internas',
    'Oficina de Calidad Operativa y Cumplimiento Interno',
    '5 días hábiles',
    'Sistema interno de quejas y cumplimiento',
    'Alta'
);