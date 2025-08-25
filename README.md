# 🐦 Paloma Licitera - Dashboard de Licitaciones Gubernamentales

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13%2B-blue.svg)](https://postgresql.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)

Sistema completo para monitoreo y análisis de licitaciones gubernamentales de México.

## 🚀 Instalación Rápida

```bash
git clone https://github.com/abueloide/paloma-licitera-new.git
cd paloma-licitera-new
chmod +x install.sh
./install.sh
```

**¡IMPORTANTE!** La primera instalación incluye **descarga inicial REAL** de 12 meses que puede tomar 30-60 minutos.

## 📊 Fuentes de Datos

| Fuente | Registros Esperados | Cobertura | Actualización |
|--------|-------------------|-----------|---------------|
| **ComprasMX** | ~50,000-100,000 | Federal (México) | Cada 6 horas |
| **DOF** | ~5,000-10,000 | Diario Oficial | Martes y Jueves |
| **Tianguis Digital** | ~10,000-20,000 | CDMX | Cada 6 horas |
| **Sitios Masivos** | ~5,000-15,000 | Múltiples estados | Semanal |

## 🎯 Diferencias Críticas: Descarga Inicial vs Incremental

### 🚀 DESCARGA INICIAL (Solo primera vez)
```bash
./run-scheduler.sh descarga-inicial --desde=2024-01-01
```

**¿Qué hace?**
- ✅ **ComprasMX**: Descarga MASIVA de 50,000-100,000 licitaciones
- ✅ **DOF**: Genera y procesa TODAS las fechas martes/jueves de 12 meses  
- ✅ **Tianguis**: Descarga MASIVA de 10,000-20,000 licitaciones
- ✅ **Sitios Masivos**: Recorre TODOS los sitios gubernamentales disponibles

**Tiempo:** 30-60 minutos  
**Cuándo usar:** Solo la primera vez o si la BD está vacía

### 🔄 ACTUALIZACIÓN INCREMENTAL (Uso regular)
```bash
./run-scheduler.sh incremental
```

**¿Qué hace?**
- ✅ **ComprasMX**: Solo licitaciones nuevas desde la última ejecución
- ✅ **DOF**: Solo si es martes/jueves y no se ha ejecutado hoy
- ✅ **Tianguis**: Solo registros nuevos desde el último UUID
- ❌ **Sitios Masivos**: No se ejecuta (solo domingos)

**Tiempo:** 5-15 minutos  
**Cuándo usar:** Para actualizaciones regulares

## 🛠️ Comandos Principales

### 📊 Estado y Estadísticas
```bash
./run-scheduler.sh status          # Ver estado completo del sistema
./run-scheduler.sh stats --dias=30 # Estadísticas de 30 días
```

### 🔍 Descargas Específicas
```bash
# Histórico de una fuente específica
./run-scheduler.sh historico --fuente=comprasmx --desde=2024-06-01

# Solo ComprasMX incremental
./run-scheduler.sh incremental --fuente=comprasmx
```

### 🐳 Comandos Docker
```bash
docker-compose logs -f              # Ver logs en tiempo real
docker-compose logs postgres        # Solo logs de PostgreSQL  
docker-compose logs scheduler       # Solo logs del scheduler
./docker-stop.sh                    # Detener todos los servicios
./cleanup.sh                        # Limpiar completamente
```

## 📈 Acceso al Dashboard

- **Dashboard Principal**: http://localhost:8000
- **API Documentación**: http://localhost:8000/docs
- **API Redoc**: http://localhost:8000/redoc

## 🔧 Arquitectura Técnica

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend       │    │   Database      │
│   React + TS    │◄──►│   FastAPI        │◄──►│   PostgreSQL    │
│   Tailwind      │    │   Python 3.8+   │    │   puerto 5432   │
│   puerto 5173   │    │   puerto 8000    │    └─────────────────┘
└─────────────────┘    └──────────────────┘              ▲
                                ▲                        │
                       ┌─────────────────┐               │
                       │   Scheduler     │               │
                       │   Automatizado  │───────────────┘
                       │   ETL + Scrapers│
                       └─────────────────┘
```

### Componentes Principales:

1. **API FastAPI** (`src/api.py`): Servidor principal con 15+ endpoints
2. **Scheduler** (`src/scheduler/`): Orquestador de descargas automatizadas  
3. **ETL** (`src/etl.py`): Procesamiento y transformación de datos
4. **Scrapers** (`etl-process/extractors/`): Extractores específicos por fuente
5. **Frontend** (`frontend/`): Interfaz React con componentes modernos

## 🗂️ Estructura de Archivos

```
paloma-licitera-new/
├── 🐳 docker-compose.yml           # Configuración Docker
├── 🚀 install.sh                   # Instalador principal  
├── ⚙️  config.yaml                  # Configuración general
├── src/
│   ├── 🌐 api.py                   # API FastAPI principal
│   ├── 📊 etl.py                   # Orquestador ETL
│   ├── 💾 database.py              # Conexión PostgreSQL
│   └── scheduler/                  # Sistema de automatización
│       ├── 🎯 __main__.py          # CLI del scheduler
│       ├── 🧠 scheduler_manager.py # Lógica principal
│       └── 🔗 scraper_wrappers.py  # Wrappers de scrapers
├── etl-process/extractors/         # Scrapers especializados
│   ├── comprasMX/                  # Portal Federal de Compras
│   ├── dof/                        # Diario Oficial
│   ├── tianguis-digital/           # CDMX
│   └── sitios-masivos/             # Múltiples sitios
├── frontend/                       # React + TypeScript
│   ├── src/
│   │   ├── components/             # Componentes UI
│   │   ├── services/api.ts         # Cliente API
│   │   └── types/                  # Tipos TypeScript
│   └── package.json
└── 📋 run-scheduler.sh             # CLI para comandos
```

## 🎛️ Configuración Avanzada

### Variables de Entorno
```bash
# Base de datos
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=paloma_licitera
DATABASE_USER=postgres
DATABASE_PASSWORD=tu_password

# Para scrapers
PALOMA_MODE=incremental|historical|descarga_inicial
PALOMA_MASSIVE_DOWNLOAD=true|false
DOF_FECHA_DESDE=2024-01-01
```

### Automatización
El sistema incluye scheduler automático que ejecuta:
- **Diario 6:00 AM**: Todas las fuentes incrementales
- **Cada 6 horas**: ComprasMX y Tianguis  
- **Martes/Jueves 9:00 AM y 9:00 PM**: DOF
- **Domingos 2:00 AM**: Sitios masivos

## 📊 Endpoints API Principales

| Endpoint | Descripción |
|----------|-------------|
| `GET /stats` | Estadísticas generales |
| `GET /licitaciones` | Listado con filtros avanzados |
| `GET /filtros` | Valores únicos para filtros |
| `GET /analisis/por-tipo-contratacion` | Análisis por tipo |
| `GET /analisis/por-dependencia` | Análisis por entidad |  
| `GET /analisis/temporal` | Análisis temporal |
| `GET /detalle/{id}` | Detalle de licitación |
| `GET /busqueda-rapida` | Autocompletado |

## 🚨 Troubleshooting

### Problema: PostgreSQL no inicia
```bash
docker-compose logs postgres
docker-compose down -v
docker-compose up -d postgres
```

### Problema: API no responde
```bash
docker-compose logs paloma-app
docker-compose restart paloma-app
```

### Problema: Scheduler con errores
```bash
docker-compose logs scheduler
./run-scheduler.sh status
```

### Problema: Puerto ocupado
```bash
lsof -i :8000      # Ver qué usa el puerto
lsof -ti :8000 | xargs kill -9  # Matar proceso
```

## 🔄 Flujo de Datos Típico

1. **Scrapers** extraen datos de fuentes gubernamentales
2. **ETL** procesa y normaliza los datos  
3. **PostgreSQL** almacena datos estructurados
4. **API FastAPI** sirve datos via REST
5. **Frontend React** presenta dashboard interactivo

## 💡 Tips de Rendimiento

- **Primera instalación**: Ejecutar en horario nocturno por la duración
- **Actualizaciones**: `./run-scheduler.sh incremental` cada mañana
- **Monitoreo**: `./run-scheduler.sh status` para verificar estado
- **Mantenimiento**: `./cleanup.sh` solo si hay problemas graves

## 🤝 Contribución

1. Fork el proyecto
2. Crear branch de feature (`git checkout -b feature/amazing-feature`)
3. Commit cambios (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para detalles.

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/abueloide/paloma-licitera-new/issues)
- **Documentación**: Ver código fuente y comentarios
- **Logs**: `docker-compose logs -f` para debugging

---

**🐦 Paloma Licitera** - Desarrollado con ❤️ para transparencia gubernamental