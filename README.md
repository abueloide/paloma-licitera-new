# Paloma Licitera - Versión Simplificada

## 📋 Descripción
Sistema ETL para procesar licitaciones gubernamentales de México desde múltiples fuentes.

## 🚀 Inicio Rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
python src/database.py --setup

# Ejecutar ETL completo
python src/etl.py --all

# Iniciar API
python src/api.py
```

## 📁 Estructura

```
paloma-licitera-new/
├── src/
│   ├── extractors/      # Extractores por fuente
│   ├── database.py      # Gestión de BD
│   ├── etl.py          # Orquestador principal
│   └── api.py          # API REST
├── config.yaml         # Configuración
├── requirements.txt    # Dependencias
└── data/              # Datos procesados
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
- `GET /health` - Estado del sistema
- `GET /licitaciones` - Lista de licitaciones con filtros
- `GET /licitaciones/{id}` - Detalle de licitación
- `GET /stats` - Estadísticas generales
- `GET /filters` - Valores únicos para filtros
- `POST /etl/run` - Ejecutar proceso ETL

### Ejemplos de uso

```bash
# Obtener todas las licitaciones
curl http://localhost:8000/licitaciones

# Filtrar por fuente
curl http://localhost:8000/licitaciones?fuente=COMPRASMX

# Buscar por texto
curl http://localhost:8000/licitaciones?q=mantenimiento

# Ejecutar ETL
curl -X POST http://localhost:8000/etl/run?fuente=all
```

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