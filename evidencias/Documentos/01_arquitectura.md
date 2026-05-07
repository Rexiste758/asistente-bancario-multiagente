@'

\# Evidencia de arquitectura segmentada



El proyecto separa responsabilidades en los siguientes componentes:



<table>

&#x20; <thead>

&#x20;   <tr>

&#x20;     <th>Componente</th>

&#x20;     <th>Archivo principal</th>

&#x20;     <th>Responsabilidad</th>

&#x20;   </tr>

&#x20; </thead>

&#x20; <tbody>

&#x20;   <tr>

&#x20;     <td>CLI</td>

&#x20;     <td><code>app/principal.py</code></td>

&#x20;     <td>Entrada del usuario y comandos de prueba.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Orquestador</td>

&#x20;     <td><code>app/agentes/orquestador.py</code></td>

&#x20;     <td>Controla flujo, memoria y ruteo.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Catálogo</td>

&#x20;     <td><code>app/agentes/catalogo\_procesos.py</code></td>

&#x20;     <td>Relaciona procesos, agentes y documentos.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Agentes especializados</td>

&#x20;     <td><code>app/agentes/agentes\_proceso.py</code></td>

&#x20;     <td>Agentes por proceso operativo.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Base común de agentes</td>

&#x20;     <td><code>app/agentes/agente\_especializado\_base.py</code></td>

&#x20;     <td>Lógica compartida de clasificación y respuesta.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Tool RAG</td>

&#x20;     <td><code>app/herramientas/herramienta\_rag.py</code></td>

&#x20;     <td>Recuperación documental.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Tool BD</td>

&#x20;     <td><code>app/herramientas/herramienta\_bd.py</code></td>

&#x20;     <td>Consultas estructuradas.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Memoria</td>

&#x20;     <td><code>app/memoria/memoria\_conversacional.py</code></td>

&#x20;     <td>Contexto conversacional.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Ingesta RAG</td>

&#x20;     <td><code>app/rag/ingesta.py</code></td>

&#x20;     <td>Chunking, embeddings y almacenamiento vectorial.</td>

&#x20;   </tr>

&#x20;   <tr>

&#x20;     <td>Cliente LLM</td>

&#x20;     <td><code>app/llm/cliente\_llm.py</code></td>

&#x20;     <td>Comunicación con DeepSeek.</td>

&#x20;   </tr>

&#x20; </tbody>

</table>

'@ | Set-Content -Path "evidencias\\Documentos\\01\_arquitectura.md" -Encoding UTF8

