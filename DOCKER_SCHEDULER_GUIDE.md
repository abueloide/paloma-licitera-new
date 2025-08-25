# 🐳 PALOMA LICITERA - GUÍA DE USO DOCKER + SCHEDULER

## 🚀 INSTALACIÓN Y CONFIGURACIÓN

### 1. Preparar el entorno
```bash
# Clonar repositorio
git clone https://github.com/abueloide/paloma-licitera-new.git
cd paloma-licitera-new

# Dar permisos a scripts
chmod +x docker-start.sh docker-stop.sh run-scheduler.sh
```

### 2. Iniciar servicios
```bash
# Iniciar todos los servicios (PostgreSQL + API + Scheduler)
./docker-start.sh
```

Esto iniciará:
- **PostgreSQL**: Puerto 5432
- **API REST**: http://localhost:8000  
- **Scheduler**: Modo daemon activo

### 3. Verificar que todo funciona
```bash
# Verificar estado del sistema
./run-scheduler.sh status

# Ver logs
docker-compose logs -f scheduler
docker-compose logs -f paloma-app
```

## 📋 COMANDOS DISPONIBLES

### Estado del Sistema
```bash
# Estado completo del sistema
./run-scheduler.sh status

# Estadísticas (en desarrollo)
./run-scheduler.sh stats --dias=30
```

### Actualizaciones Incrementales
```bash
# Ejecutar actualización incremental (todas las fuentes)
./run-scheduler.sh incremental

# Solo una fuente específica
./run-scheduler.sh incremental --fuente=comprasmx
./run-scheduler.sh incremental --fuente=dof
./run-scheduler.sh incremental --fuente=tianguis
```

### Descargas Históricas
```bash
# Descarga histórica completa desde fecha
./run-scheduler.sh historico --fuente=all --desde=2025-01-01

# Solo una fuente específica
./run-scheduler.sh historico --fuente=comprasmx --desde=2025-01-01
./run-scheduler.sh historico --fuente=dof --desde=2025-01-01
./run-scheduler.sh historico --fuente=tianguis --desde=2025-01-01
```

### Ejecuciones Batch Programadas
```bash
# Batch diario (06:00 AM)
./run-scheduler.sh batch diario

# Batch cada 6 horas
./run-scheduler.sh batch cada_6h

# Batch semanal (domingos 02:00 AM)
./run-scheduler.sh batch semanal
```

## 🔄 AUTOMATIZACIÓN

### Scheduler Daemon
El scheduler se ejecuta automáticamente en modo daemon cuando se inicia con Docker. Revisa:
- Actualizaciones incrementales cada hora
- **DOF solo martes y jueves entre 9:00-10:00 AM y 21:00-22:00 PM**
- Sitios masivos los domingos

### Horarios de Ejecución por Fuente

#### 📅 **DOF (Diario Oficial de la Federación)**
- **Días**: Solo martes y jueves
- **Horarios**: 
  - **Matutino**: 9:00 AM - 10:00 AM 
  - **Vespertino**: 9:00 PM - 10:00 PM
- **Zona horaria**: America/Mexico_City
- **Lógica**: Solo ejecuta una vez por día, respetando horarios oficiales de publicación

#### 🏢 **ComprasMX**
- **Frecuencia**: Cada 6 horas
- **Horarios**: 00:00, 06:00, 12:00, 18:00
- **Modo**: Incremental basado en último expediente procesado

#### 🏛️ **Tianguis Digital CDMX**
- **Frecuencia**: Cada 6 horas  
- **Horarios**: 00:00, 06:00, 12:00, 18:00
- **Modo**: Incremental basado en último UUID procesado

#### 📊 **Sitios Masivos**
- **Frecuencia**: Semanal
- **Día**: Domingos a las 02:00 AM
- **Modo**: Procesamiento completo

### Configuración Automática
Editar `config.yaml` para cambiar:
- Horarios de ejecución
- Fuentes habilitadas/deshabilitadas
- Intervalos de actualización
- Configuración de base de datos

```yaml
# Configuración DOF actualizada
dof_config:
  check_times: ["09:00", "21:00"]  # Exactamente 9 AM y 9 PM
  retry_attempts: 3
  retry_delay: 300  # 5 minutos
```

## 🗃️ GESTIÓN DE DATOS

### Directorios de Datos
```
data/
├── raw/          # Datos crudos de scrapers
├── processed/    # Datos procesados 
└── logs/         # Logs del sistema
```

### Base de Datos
```bash
# Acceder a PostgreSQL directamente
docker-compose exec postgres psql -U postgres -d paloma_licitera

# Ver estadísticas de registros
docker-compose exec postgres psql -U postgres -d paloma_licitera -c "
SELECT fuente, COUNT(*) as total, 
       MAX(fecha_captura) as ultima_actualizacion
FROM licitaciones 
GROUP BY fuente ORDER BY total DESC;"
```

## 🔧 TROUBLESHOOTING

### Verificar servicios
```bash
# Estado de contenedores
docker-compose ps

# Logs detallados
docker-compose logs scheduler
docker-compose logs paloma-app
docker-compose logs postgres
```

### Reiniciar servicios
```bash
# Reiniciar todo
./docker-stop.sh
./docker-start.sh

# Reiniciar solo scheduler
docker-compose restart scheduler

# Reconstruir contenedores
docker-compose down
docker-compose build
docker-compose up -d
```

### Problemas comunes

**Error de conexión a base de datos:**
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose exec postgres pg_isready -U postgres

# Reiniciar PostgreSQL
docker-compose restart postgres
```

**DOF no ejecuta cuando debería:**
```bash
# Verificar día de la semana y hora
./run-scheduler.sh status | jq '.fuentes.dof'

# Ver logs específicos de DOF
docker-compose logs scheduler | grep DOF

# Forzar ejecución manual
./run-scheduler.sh incremental --fuente=dof
```

**Scheduler no responde:**
```bash
# Verificar logs
docker-compose logs -f scheduler

# Entrar al contenedor
docker-compose exec scheduler bash
python -m src.scheduler status
```

## 📊 MONITOREO

### API Web
- Dashboard: http://localhost:8000
- Documentación API: http://localhost:8000/docs
- Estado: http://localhost:8000/stats

### Logs en tiempo real
```bash
# Todos los servicios
docker-compose logs -f

# Solo scheduler
docker-compose logs -f scheduler

# Solo API
docker-compose logs -f paloma-app

# Filtrar por fuente
docker-compose logs scheduler | grep "DOF"
docker-compose logs scheduler | grep "ComprasMX"
```

### Métricas importantes
```bash
# Verificar último procesamiento por fuente
./run-scheduler.sh status | jq '.ultimo_procesamiento'

# Ver estado de DOF específicamente
./run-scheduler.sh status | jq '.fuentes.dof'

# Total de registros por fuente
./run-scheduler.sh status | jq '.database.by_source'

# Verificar horarios de DOF
./run-scheduler.sh status | jq '.scheduler_config.dof_config'
```

## 🕘 HORARIOS Y PROGRAMACIÓN

### Verificar próxima ejecución DOF
```bash
# Ver estado de fuentes
./run-scheduler.sh status

# Logs recientes de DOF
docker-compose logs scheduler | grep "DOF" | tail -10

# Verificar día y hora actual
date
```

### Forzar ejecución inmediata
```bash
# Forzar DOF (ignorar horarios)
./run-scheduler.sh historico --fuente=dof --desde=2025-01-20

# Actualización incremental de todas las fuentes
./run-scheduler.sh incremental
```

## 🛑 DETENER SERVICIOS

```bash
# Detener todos los servicios
./docker-stop.sh

# Detener y limpiar todo (incluyendo volúmenes)
docker-compose down -v
```

## 🔧 DESARROLLO Y DEBUGGING

### Acceso directo a contenedores
```bash
# Acceder al scheduler
docker-compose exec scheduler bash

# Acceder a PostgreSQL
docker-compose exec postgres psql -U postgres -d paloma_licitera

# Ejecutar comandos manualmente
docker-compose exec scheduler python -m src.scheduler --help
```

### Testing de horarios DOF
```bash
# Simular ejecución DOF
docker-compose exec scheduler python -c "
from src.scheduler.scraper_wrappers import DOFWrapper
from src.scheduler.database_queries import DatabaseQueries
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

db = DatabaseQueries(config)
wrapper = DOFWrapper(config, db)
print(f'Should run today: {wrapper.should_run_today()}')
"
```

### Modo desarrollo local (sin Docker)
```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export DATABASE_HOST=localhost
export DATABASE_USER=postgres
export DATABASE_PASSWORD=tu_password

# Ejecutar scheduler localmente
python -m src.scheduler status
python -m src.scheduler incremental
```

---

## 📈 PRÓXIMOS PASOS

1. **Monitoreo avanzado**: Implementar métricas y alertas
2. **Web UI**: Panel de control web para el scheduler
3. **Notificaciones**: Alertas por email/Slack cuando DOF se ejecute
4. **Backup automático**: Respaldo programado de la BD
5. **Escalamiento**: Múltiples workers para paralelización

---

## 🆘 SOPORTE

Para problemas o preguntas:
1. Revisar logs: `docker-compose logs -f scheduler`
2. Verificar estado: `./run-scheduler.sh status`
3. Revisar configuración: `config.yaml`
4. Documentación API: http://localhost:8000/docs

### Problemas específicos de DOF:
- Verificar que es martes o jueves
- Confirmar que la hora está entre 9:00-10:00 AM o 21:00-22:00 PM
- Revisar que no se haya ejecutado ya hoy
- Revisar logs: `docker-compose logs scheduler | grep DOF`