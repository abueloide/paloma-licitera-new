# 🔧 SOLUCIÓN RÁPIDA - Dashboard No Funciona

## ⚡ Inicio Rápido (5 minutos)

**El problema**: El frontend no se conecta al backend porque estaban usando APIs incompatibles.

**La solución**: Usar el API correcto y seguir estos pasos:

### 1. Hacer los scripts ejecutables
```bash
chmod +x start_dashboard.sh stop_dashboard.sh
```

### 2. Ejecutar el dashboard completo
```bash
./start_dashboard.sh
```

Esto iniciará:
- ✅ Backend SQLite-compatible en http://localhost:8000
- ✅ Frontend con proxy configurado en http://localhost:3001
- ✅ Creación automática de base de datos si no existe

### 3. Si algo no funciona...

**Verificar que los puertos estén libres:**
```bash
# Detener cualquier proceso previo
./stop_dashboard.sh

# O manualmente:
pkill -f "uvicorn"
pkill -f "vite"
```

**Verificar que el API responda:**
```bash
curl http://localhost:8000/
```

**Ver logs en tiempo real:**
```bash
# Backend
tail -f logs/backend.log

# Frontend  
tail -f logs/frontend.log
```

### 4. Si necesitas datos de prueba

```bash
# Ejecutar ETL para obtener datos
python -m src.etl
```

## 🎯 Lo que se solucionó

### ✅ Proxy Frontend configurado
- El frontend ahora puede hacer llamadas al backend via `/api`
- Configuración de proxy en `vite.config.ts`

### ✅ API SQLite compatible creado
- Nuevo archivo `src/api_sqlite.py` con todos los endpoints que el frontend necesita
- Compatible con SQLite (no requiere PostgreSQL)
- Mismos endpoints que esperaba el frontend

### ✅ Fechas corregidas
- Tabla de licitaciones ahora muestra "Fecha Pub." y "Fecha Apertura"
- Formato dd/MM/yyyy consistente

### ✅ Scripts de inicio mejorados
- `start_dashboard.sh` inicia todo automáticamente
- `stop_dashboard.sh` detiene los servicios
- Creación automática de BD si no existe

## 🔍 Verificación Rápida

Una vez iniciado el dashboard, verifica:

1. **Backend funcionando**: http://localhost:8000 debe mostrar info de la API
2. **Dashboard cargando**: http://localhost:3001 debe mostrar el dashboard
3. **Datos conectados**: El dashboard debe mostrar estadísticas sin errores
4. **Tabla completa**: La tabla de licitaciones debe tener ambas columnas de fecha

## 🚨 Problemas Comunes

### "Error de conexión al servidor"
- Verificar que el backend esté ejecutándose en puerto 8000
- Revisar `logs/backend.log` para errores

### "No aparecen datos"
- Ejecutar ETL: `python -m src.etl` 
- Verificar que `licitaciones.db` exista y tenga datos

### "Puerto en uso"
- Ejecutar `./stop_dashboard.sh` primero
- O cambiar puertos en los archivos de configuración

### Permisos en Linux/Mac
```bash
chmod +x *.sh
```

---

## 📊 Estado Actual

- ✅ **Frontend**: React + Vite + Proxy configurado
- ✅ **Backend**: FastAPI + SQLite + Endpoints completos  
- ✅ **Base de Datos**: SQLite con esquema correcto
- ✅ **Scripts**: Inicio/parada automatizados
- ✅ **Fechas**: Ambas fechas mostradas correctamente

**Resultado**: Dashboard completamente funcional en http://localhost:3001

---

*Para más detalles técnicos, ver el README.md principal.*