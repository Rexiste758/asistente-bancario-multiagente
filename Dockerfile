FROM python:3.12-slim

# Evita que Python genere archivos .pyc y permite ver logs en tiempo real.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Carpeta principal del proyecto dentro del contenedor.
ENV PYTHONPATH=/proyecto
WORKDIR /proyecto

# Dependencias del sistema necesarias para librerías de embeddings y vector store.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Primero copiamos requirements para aprovechar la caché de Docker.
COPY requirements.txt .

# Instalamos las librerías de Python dentro del contenedor.
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del proyecto.
COPY . .

# Comando por defecto del contenedor
CMD ["python", "-m", "app.principal", "health"]