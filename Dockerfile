FROM python:3.11-slim

# Instalar dependencias del sistema para PostgreSQL y Playwright
RUN apt-get update && apt-get install -y \
    postgresql-client \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Instalar Playwright browsers
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps

WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorios de datos
RUN mkdir -p data/raw data/processed logs

# Exponer puerto API
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/api.py"]