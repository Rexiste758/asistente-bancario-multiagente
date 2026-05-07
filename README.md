\# Asistente Bancario Multiagente - BANCOMEX



Asistente conversacional interno para consultas sobre procesos operativos bancarios de BANCOMEX.  

El sistema usa arquitectura multiagente, recuperación documental mediante RAG, consultas estructuradas a una base de datos relacional y memoria conversacional en sesión.



\---



\## 1. Objetivo



El objetivo del proyecto es construir un asistente conversacional interno capaz de:



\- Responder preguntas documentales usando RAG sobre documentos Word.

\- Consultar datos estructurados en una base SQLite.

\- Mantener contexto conversacional entre turnos.

\- Separar responsabilidades entre orquestador, agentes especializados y herramientas.

\- Entregar trazabilidad de las fuentes utilizadas: orquestador, LLM, RAG y base de datos.



\---



\## 2. Procesos cubiertos



El sistema cubre cinco procesos operativos internos:



| Código | Proceso operativo | Agente especializado | Documento RAG |

|---|---|---|---|

| A | Atención de aclaraciones bancarias | AgenteAclaraciones | A\_aclaraciones\_bancarias.docx |

| B | Cancelación de productos financieros | AgenteCancelacion | B\_cancelacion\_productos.docx |

| C | Escalamiento de incidencias operativas | AgenteIncidencias | C\_escalamiento\_incidencias.docx |

| D | Actualización de datos del cliente | AgenteDatosCliente | D\_actualizacion\_datos\_cliente.docx |

| E | Gestión de quejas internas | AgenteQuejas | E\_quejas\_internas.docx |



\---



\## 3. Arquitectura general



La arquitectura implementada sigue este flujo:



```text

CLI

&#x20;↓

SolicitudAgente

&#x20;↓

OrquestadorAgentes

&#x20;↓

Clasificador de ruta conversacional

&#x20;↓

Agente especializado

&#x20;↓

Clasificador controlado de herramientas

&#x20;↓

RAGTool / DatabaseTool

&#x20;↓

Cliente LLM

&#x20;↓

RespuestaAgente con trazabilidad







\## 3.1 Diagrama de arquitectura



```mermaid

flowchart TD

&#x20;   U\[Usuario] --> CLI\[CLI / app.principal]

&#x20;   CLI --> S\[SolicitudAgente]



&#x20;   S --> O\[OrquestadorAgentes]



&#x20;   O --> M\[Memoria Conversacional]

&#x20;   O --> C\[Catálogo de Procesos]

&#x20;   O --> LLMR\[LLM Clasificador de Ruta]



&#x20;   LLMR -->|orientación| RO\[Respuesta controlada]

&#x20;   LLMR -->|fuera de alcance| RF\[Respuesta fuera de alcance]

&#x20;   LLMR -->|proceso A-E| AE\[Agente Especializado]

&#x20;   LLMR -->|usar memoria| AE



&#x20;   AE --> LLMH\[LLM Clasificador de Herramientas]

&#x20;   LLMH -->|documental| RAG\[RAGTool]

&#x20;   LLMH -->|estructurado| BD\[DatabaseTool]

&#x20;   LLMH -->|mixto| RAG

&#x20;   LLMH -->|mixto| BD



&#x20;   RAG --> VS\[ChromaDB / Vector Store]

&#x20;   BD --> SQL\[SQLite / procesos\_operativos]



&#x20;   VS --> CTX\[Contexto recuperado]

&#x20;   SQL --> DATA\[Dato estructurado]



&#x20;   CTX --> LLMF\[LLM Respuesta Final]

&#x20;   DATA --> LLMF



&#x20;   LLMF --> RA\[RespuestaAgente con trazabilidad]

&#x20;   RO --> RA

&#x20;   RF --> RA

```





\## 3.2 Flujo conversacional



```mermaid

sequenceDiagram

&#x20;   participant U as Usuario

&#x20;   participant CLI as CLI

&#x20;   participant O as Orquestador

&#x20;   participant MEM as Memoria

&#x20;   participant CAT as Catálogo

&#x20;   participant AE as Agente Especializado

&#x20;   participant RAG as RAGTool

&#x20;   participant BD as DatabaseTool

&#x20;   participant LLM as Cliente LLM



&#x20;   U->>CLI: Envía mensaje

&#x20;   CLI->>O: SolicitudAgente

&#x20;   O->>MEM: Consulta contexto conversacional

&#x20;   O->>CAT: Evalúa proceso posible

&#x20;   O->>LLM: Clasifica ruta conversacional



&#x20;   alt Orientación o fuera de alcance

&#x20;       O-->>CLI: Respuesta controlada

&#x20;   else Proceso detectado

&#x20;       O->>AE: Invoca agente del proceso

&#x20;       AE->>LLM: Clasifica herramienta necesaria



&#x20;       alt Pregunta documental

&#x20;           AE->>RAG: Recupera chunks

&#x20;           RAG-->>AE: Evidencia documental

&#x20;       else Pregunta estructurada

&#x20;           AE->>BD: Ejecuta query predefinida

&#x20;           BD-->>AE: Dato estructurado

&#x20;       else Pregunta mixta

&#x20;           AE->>RAG: Recupera chunks

&#x20;           AE->>BD: Ejecuta query predefinida

&#x20;       end



&#x20;       AE->>LLM: Redacta respuesta con evidencia

&#x20;       LLM-->>AE: Respuesta final

&#x20;       AE-->>O: Resultado con trazabilidad

&#x20;       O->>MEM: Actualiza memoria

&#x20;       O-->>CLI: RespuestaAgente

&#x20;   end



&#x20;   CLI-->>U: Muestra respuesta

```







\## 3.3 Decisión de herramientas del agente especializado



```mermaid

flowchart TD

&#x20;   P\[Pregunta del usuario] --> AE\[Agente especializado del proceso]

&#x20;   AE --> CL\[LLM clasificador controlado]



&#x20;   CL -->|Explicación, flujo, validaciones, escalamiento| RAG\[RAGTool]

&#x20;   CL -->|Área, tiempo, canal, criticidad| BD\[DatabaseTool]

&#x20;   CL -->|Explicación + dato puntual| MIX\[RAGTool + DatabaseTool]



&#x20;   RAG --> DOC\[Documento Word indexado en ChromaDB]

&#x20;   BD --> SQL\[SQLite con queries predefinidas]

&#x20;   MIX --> DOC

&#x20;   MIX --> SQL



&#x20;   DOC --> RESP\[Respuesta final con evidencia]

&#x20;   SQL --> RESP

```





\## 3.4 Uso de memoria conversacional



```mermaid

flowchart TD

&#x20;   U1\[Usuario: Explícame aclaraciones] --> O1\[Orquestador]

&#x20;   O1 --> A\[Proceso A detectado]

&#x20;   A --> M1\[Memoria guarda último\_proceso\_id = A]



&#x20;   U2\[Usuario: ¿Y cuánto tarda?] --> O2\[Orquestador]

&#x20;   O2 --> M2\[Consulta memoria]

&#x20;   M2 --> A2\[Recupera proceso A]

&#x20;   A2 --> AG\[AgenteAclaraciones]

&#x20;   AG --> BD\[DatabaseTool]

&#x20;   BD --> R\[Respuesta: 48 horas hábiles]

```

