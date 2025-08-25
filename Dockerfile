# Usar imagen oficial de Playwright con Python (Ubuntu 24.04 LTS Noble)
FROM mcr.microsoft.com/playwright/python:v1.54.0-noble

# Configurar variables de entorno
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar PostgreSQL client y otras dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear directorios necesarios
RUN mkdir -p data/raw data/processed logs

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/api.py"]