FROM python:3.11-slim

# Actualizar packages y instalar dependencias base
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

# Instalar dependencias Python básicas
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright después de tener todo configurado
RUN pip install --no-cache-dir playwright==1.45.0

# Instalar solo las dependencias mínimas necesarias para Playwright
# Evitamos fuentes problemáticas y solo instalamos lo esencial
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Instalar solo Chromium sin dependencias problemáticas
RUN playwright install chromium --with-deps 2>/dev/null || playwright install chromium

# Copiar código fuente
COPY . .

# Crear directorios de datos
RUN mkdir -p data/raw data/processed logs

# Configurar variables de entorno para Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

# Exponer puerto API
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/api.py"]