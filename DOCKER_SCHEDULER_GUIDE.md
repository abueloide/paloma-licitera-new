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
- DOF solo martes y jueves después de 9:30 AM y 9:30 PM
- Sitios masivos los domingos

### Configuración Automática
Editar `config.yaml` para cambiar:
- Horarios de ejecución
- Fuentes habilitadas/deshabilitadas
- Intervalos de actualización
- Configuración de base de datos

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
```

### Métricas importantes
```bash
# Verificar último procesamiento por fuente
./run-scheduler.sh status | jq '.ultimo_procesamiento'

# Ver fuentes habilitadas
./run-scheduler.sh status | jq '.fuentes'

# Total de registros por fuente
./run-scheduler.sh status | jq '.database.by_source'
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
3. **Notificaciones**: Alertas por email/Slack
4. **Backup automático**: Respaldo programado de la BD
5. **Escalamiento**: Múltiples workers para paralelización

---

## 🆘 SOPORTE

Para problemas o preguntas:
1. Revisar logs: `docker-compose logs -f scheduler`
2. Verificar estado: `./run-scheduler.sh status`
3. Revisar configuración: `config.yaml`
4. Documentación API: http://localhost:8000/docs