\# Evidencia de arquitectura segmentada



El proyecto separa responsabilidades en los siguientes componentes:



| Componente | Archivo principal | Responsabilidad |

|---|---|---|

| CLI | app/principal.py | Entrada del usuario y comandos de prueba |

| Orquestador | app/agentes/orquestador.py | Controla flujo, memoria y ruteo |

| Catálogo | app/agentes/catalogo\_procesos.py | Relaciona procesos, agentes y documentos |

| Agentes especializados | app/agentes/agentes\_proceso.py | Agentes por proceso operativo |

| Base común de agentes | app/agentes/agente\_especializado\_base.py | Lógica compartida de clasificación y respuesta |

| Tool RAG | app/herramientas/herramienta\_rag.py | Recuperación documental |

| Tool BD | app/herramientas/herramienta\_bd.py | Consultas estructuradas |

| Memoria | app/memoria/memoria\_conversacional.py | Contexto conversacional |

| Ingesta RAG | app/rag/ingesta.py | Chunking, embeddings y almacenamiento vectorial |

| Cliente LLM | app/llm/cliente\_llm.py | Comunicación con DeepSeek |

