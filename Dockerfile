FROM python:3.11-slim

# Actualizar packages 
RUN apt-get update

# Instalar dependencias básicas del sistema
RUN apt-get install -y \
    postgresql-client \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primero para cache de Docker
COPY requirements.txt .

# Instalar dependencias Python (sin Playwright)
RUN pip install --no-cache-dir --upgrade pip

# Crear requirements temporal sin playwright
RUN grep -v playwright requirements.txt > requirements_temp.txt || cp requirements.txt requirements_temp.txt

# Instalar dependencias básicas
RUN pip install --no-cache-dir -r requirements_temp.txt

# Instalar Playwright por separado con configuración específica
RUN pip install --no-cache-dir playwright==1.45.0

# Configurar Playwright sin validaciones de host problemáticas  
ENV PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Instalar solo chromium sin dependencias del sistema
RUN playwright install chromium

# Copiar código fuente
COPY . .

# Limpiar archivos temporales
RUN rm -f requirements_temp.txt

# Crear directorios necesarios
RUN mkdir -p data/raw data/processed logs

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/api.py"]