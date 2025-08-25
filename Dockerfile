# Usar imagen base con más herramientas ya instaladas
FROM python:3.11

# Configurar variables de entorno para evitar interacciones
ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Actualizar sistema e instalar dependencias básicas
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

# Instalar solo chromium browser sin dependencias del sistema
RUN python -c "import playwright; playwright.install(['chromium'])"

# Copiar el resto del código
COPY . .

# Crear directorios necesarios
RUN mkdir -p data/raw data/processed logs

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/api.py"]