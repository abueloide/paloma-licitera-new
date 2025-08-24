# Paloma Licitera - Versión Simplificada

## 📋 Descripción
Sistema ETL para procesar licitaciones gubernamentales de México desde múltiples fuentes con frontend web moderno.

## 🚀 Inicio Rápido

### Backend (API)
```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
python src/database.py --setup

# Ejecutar ETL completo
python src/etl.py --all

# Iniciar API en puerto 8000
python src/api_enhanced.py
```

### Frontend (Dashboard Web)
```bash
# Ir a la carpeta frontend
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo en puerto 3000
npm run dev

# O usar el script de inicio
./start.sh
```

## 📁 Estructura

```
paloma-licitera-new/
├── src/
│   ├── extractors/       # Extractores por fuente
│   ├── database.py       # Gestión de BD
│   ├── etl.py           # Orquestador principal
│   ├── api.py           # API REST básica
│   └── api_enhanced.py  # API REST avanzada
├── frontend/            # Frontend React + TypeScript
│   ├── src/
│   │   ├── components/  # Componentes React
│   │   ├── pages/      # Páginas de la aplicación
│   │   ├── services/   # Servicios API
│   │   └── types/      # Definiciones TypeScript
│   ├── package.json    # Dependencias frontend
│   └── start.sh       # Script de inicio
├── config.yaml         # Configuración
├── requirements.txt     # Dependencias Python
└── data/               # Datos procesados
```

## 🔧 Configuración

Copiar `config.example.yaml` a `config.yaml` y ajustar:

```yaml
database:
  host: localhost
  port: 5432
  name: paloma_licitera
  user: tu_usuario
  password: tu_password

sources:
  comprasmx:
    enabled: true
    url: https://comprasmx.buengobierno.gob.mx
  dof:
    enabled: true
    url: https://www.dof.gob.mx
  tianguis:
    enabled: true
    url: https://tianguisdigital.cdmx.gob.mx
```

## 📊 Fuentes de Datos

1. **ComprasMX** - Portal de compras del gobierno federal
2. **DOF** - Diario Oficial de la Federación
3. **Tianguis Digital** - Portal de CDMX (formato OCDS)

## 🔌 API Endpoints

- `GET /` - Información del sistema
- `GET /stats` - Estadísticas generales
- `GET /licitaciones` - Lista de licitaciones con filtros avanzados
- `GET /licitaciones/{id}` - Detalle de licitación
- `GET /filtros` - Valores únicos para filtros
- `GET /analisis/por-tipo-contratacion` - Análisis por tipo
- `GET /analisis/por-dependencia` - Análisis por entidad
- `GET /analisis/por-fuente` - Análisis por fuente de datos
- `GET /analisis/temporal` - Análisis temporal
- `GET /busqueda-rapida` - Búsqueda rápida para autocompletado

### Ejemplos de uso

```bash
# Obtener todas las licitaciones
curl http://localhost:8000/licitaciones

# Filtrar por fuente
curl http://localhost:8000/licitaciones?fuente=COMPRASMX

# Buscar por texto
curl http://localhost:8000/licitaciones?busqueda=mantenimiento

# Obtener estadísticas
curl http://localhost:8000/stats
```

## 🌐 Frontend Web

El frontend incluye:

### 📊 **Dashboard Principal**
- Estadísticas generales del sistema
- Gráficos por fuente y estado
- Resumen de montos y totales
- Estado de última actualización

### 🔍 **Buscador de Licitaciones**
- Tabla paginada con todas las licitaciones
- Filtros avanzados (fuente, estado, tipo, entidad, fechas, montos)
- Búsqueda de texto libre
- Navegación a detalles completos

### 📈 **Análisis Avanzado**
- Análisis por tipo de contratación
- Top entidades compradoras
- Comparativa por fuente de datos
- Métricas consolidadas

### 👁️ **Vista Detallada**
- Información completa de cada licitación
- Datos estructurados y originales
- Enlaces a fuentes externas
- Historial técnico

### 🛠️ **Características Técnicas**
- **React 18** con TypeScript
- **Vite** para desarrollo rápido
- **Responsive Design** para móviles y escritorio
- **API Proxy** configurado automáticamente
- **Manejo de errores** y estados de carga
- **Navegación** con React Router

## 📦 Procesamiento de archivos ZIP

El sistema puede procesar archivos ZIP de PAAAPS del Tianguis Digital:

```python
python src/etl.py --fuente zip
```

Los archivos ZIP deben estar en: `data/processed/tianguis/*.zip`

## 🗄️ Base de Datos

El sistema usa PostgreSQL con el siguiente esquema principal:

```sql
CREATE TABLE licitaciones (
    id SERIAL PRIMARY KEY,
    numero_procedimiento VARCHAR(255) NOT NULL,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    entidad_compradora VARCHAR(500),
    tipo_procedimiento VARCHAR(50),
    tipo_contratacion VARCHAR(50),
    estado VARCHAR(50),
    fecha_publicacion DATE,
    fecha_apertura DATE,
    fecha_fallo DATE,
    monto_estimado DECIMAL(15,2),
    fuente VARCHAR(50) NOT NULL,
    url_original TEXT,
    fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash_contenido VARCHAR(64) UNIQUE,
    datos_originales JSONB
);
```

## 📝 Licencia

MIT