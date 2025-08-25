# Usar imagen base con más herramientas ya instaladas
FROM python:3.11

# Configurar variables de entorno para evitar interacciones
ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Actualizar sistema e instalar dependencias básicas + librerías para Playwright
RUN apt-get update && apt-get install -y \
    postgresql-client \
    wget \
    curl \
    ca-certificates \
    # Dependencias específicas para Playwright/Chromium
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    # Limpiar cache
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Instalar browsers de Playwright con dependencias del sistema
RUN python -m playwright install --with-deps chromium

# Copiar el resto del código
COPY . .

# Crear directorios necesarios
RUN mkdir -p data/raw data/processed logs

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["python", "src/api.py"]