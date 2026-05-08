# Asistente Bancario Multiagente - BANCOMEX

Asistente conversacional interno para consultas sobre procesos operativos bancarios de BANCOMEX.  
El sistema usa arquitectura multiagente, recuperación documental mediante RAG, consultas estructuradas a una base de datos relacional y memoria conversacional en sesión.

---

## 1. Objetivo

El objetivo del proyecto es construir un asistente conversacional interno capaz de:

- Responder preguntas documentales usando RAG sobre documentos Word.
- Consultar datos estructurados en una base SQLite.
- Mantener contexto conversacional entre turnos.
- Separar responsabilidades entre orquestador, agentes especializados y herramientas.
- Entregar trazabilidad de las fuentes utilizadas: RAG y base de datos.

---

## 2. Procesos cubiertos

El sistema cubre cinco procesos operativos internos:

| Código | Proceso operativo | Agente especializado | Documento RAG |
|---|---|---|---|
| A | Atención de aclaraciones bancarias | AgenteAclaraciones | A_aclaraciones_bancarias.docx |
| B | Cancelación de productos financieros | AgenteCancelacion | B_cancelacion_productos.docx |
| C | Escalamiento de incidencias operativas | AgenteIncidencias | C_escalamiento_incidencias.docx |
| D | Actualización de datos del cliente | AgenteDatosCliente | D_actualizacion_datos_cliente.docx |
| E | Gestión de quejas internas | AgenteQuejas | E_quejas_internas.docx |

---

## 3. Arquitectura general

La arquitectura implementada sigue este flujo:

```text
CLI
↓
SolicitudAgente
↓
OrquestadorAgentes
↓
Clasificador de ruta conversacional
↓
Agente especializado
↓
Clasificador controlado de herramientas
↓
RAGTool / DatabaseTool
↓
Cliente LLM
↓
RespuestaAgente con trazabilidad
```

## 3.1 Diagrama de arquitectura

```mermaid
flowchart TD
    U[Usuario] --> CLI[CLI / app.principal]
    CLI --> S[SolicitudAgente]

    S --> O[OrquestadorAgentes]

    O --> M[Memoria Conversacional]
    O --> C[Catálogo de Procesos]
    O --> LLMR[LLM Clasificador de Ruta]

    LLMR -->|orientación| RO[Respuesta controlada]
    LLMR -->|fuera de alcance| RF[Respuesta fuera de alcance]
    LLMR -->|proceso A-E| AE[Agente Especializado]
    LLMR -->|usar memoria| AE

    AE --> LLMH[LLM Clasificador de Herramientas]
    LLMH -->|documental| RAG[RAGTool]
    LLMH -->|estructurado| BD[DatabaseTool]
    LLMH -->|mixto| RAG
    LLMH -->|mixto| BD

    RAG --> VS[ChromaDB / Vector Store]
    BD --> SQL[SQLite / procesos_operativos]

    VS --> CTX[Contexto recuperado]
    SQL --> DATA[Dato estructurado]

    CTX --> LLMF[LLM Respuesta Final]
    DATA --> LLMF

    LLMF --> RA[RespuestaAgente con trazabilidad]
    RO --> RA
    RF --> RA
```

## 3.2 Flujo conversacional

```mermaid
sequenceDiagram
    participant U as Usuario
    participant CLI as CLI
    participant O as Orquestador
    participant MEM as Memoria
    participant CAT as Catálogo
    participant AE as Agente Especializado
    participant RAG as RAGTool
    participant BD as DatabaseTool
    participant LLM as Cliente LLM

    U->>CLI: Envía mensaje
    CLI->>O: SolicitudAgente
    O->>MEM: Consulta contexto conversacional
    O->>CAT: Evalúa proceso posible
    O->>LLM: Clasifica ruta conversacional

    alt Orientación o fuera de alcance
        O-->>CLI: Respuesta controlada
    else Proceso detectado
        O->>AE: Invoca agente del proceso
        AE->>LLM: Clasifica herramienta necesaria

        alt Pregunta documental
            AE->>RAG: Recupera chunks
            RAG-->>AE: Evidencia documental
        else Pregunta estructurada
            AE->>BD: Ejecuta query predefinida
            BD-->>AE: Dato estructurado
        else Pregunta mixta
            AE->>RAG: Recupera chunks
            AE->>BD: Ejecuta query predefinida
        end

        AE->>LLM: Redacta respuesta con evidencia
        LLM-->>AE: Respuesta final
        AE-->>O: Resultado con trazabilidad
        O->>MEM: Actualiza memoria
        O-->>CLI: RespuestaAgente
    end

    CLI-->>U: Muestra respuesta
```

## 3.3 Decisión de herramientas del agente especializado

```mermaid
flowchart TD
    P[Pregunta del usuario] --> AE[Agente especializado del proceso]
    AE --> CL[LLM clasificador controlado]

    CL -->|Explicación, flujo, validaciones, escalamiento| RAG[RAGTool]
    CL -->|Área, tiempo, canal, criticidad| BD[DatabaseTool]
    CL -->|Explicación + dato puntual| MIX[RAGTool + DatabaseTool]

    RAG --> DOC[Documento Word indexado en ChromaDB]
    BD --> SQL[SQLite con queries predefinidas]
    MIX --> DOC
    MIX --> SQL

    DOC --> RESP[Respuesta final con evidencia]
    SQL --> RESP
```

## 3.4 Uso de memoria conversacional

```mermaid
flowchart TD
    U1[Usuario: Explica aclaraciones] --> O1[Orquestador]
    O1 --> A[Proceso A detectado]
    A --> M1[Memoria guarda ultimo_proceso_id igual a A]

    U2[Usuario: Y cuanto tarda] --> O2[Orquestador]
    O2 --> M2[Consulta memoria]
    M2 --> A2[Recupera proceso A]
    A2 --> AG[AgenteAclaraciones]
    AG --> BD[DatabaseTool]
    BD --> R[Respuesta: 48 horas habiles]
```

