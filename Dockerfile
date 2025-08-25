FROM python:3.11-slim

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    postgresql-client \
    wget \
    gnupg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias Python (sin playwright primero)
RUN pip install --no-cache-dir --upgrade pip

# Instalar dependencias básicas primero
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright después de tener todo configurado
RUN pip install playwright==1.45.0

# Instalar browsers de Playwright (solo chromium para reducir tamaño)
RUN playwright install-deps chromium
RUN playwright install chromium

# Copiar código fuente
COPY . .

# Crear directorios de datos
RUN mkdir -p data/raw data/processed logs

# Exponer puerto API
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/api.py"]