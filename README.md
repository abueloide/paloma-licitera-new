# 🐦 Paloma Licitera - Dashboard de Licitaciones

Sistema de monitoreo y análisis de licitaciones gubernamentales de México.

## 🚀 Inicio Rápido

### Prerrequisitos
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+

### Instalación y Ejecución

1. **Instalar dependencias del backend:**
```bash
pip install -r requirements.txt
```

2. **Instalar dependencias del frontend:**
```bash
cd frontend
npm install
```

3. **Inicializar la base de datos:**
```bash
python -c "from src.database import DatabaseManager; db = DatabaseManager(); db.create_tables()"
```

4. **Ejecutar el proyecto completo:**
```bash
# Linux/Mac
./start_project.sh

# Windows
start_project.bat
```

Esto iniciará:
- Backend FastAPI en http://localhost:8000
- Frontend React en http://localhost:3001

## 🛠️ Desarrollo

### Backend (FastAPI)
```bash
# Ejecutar solo el backend
cd src
uvicorn api:app --reload --port 8000
```

### Frontend (React + Vite)
```bash
# Ejecutar solo el frontend
cd frontend
npm run dev
```

### ETL (Extracción de datos)
```bash
# Ejecutar proceso ETL para extraer licitaciones
python -m src.etl
```

## 📊 Características Principales

### ✅ Funcionalidades Implementadas

- **Dashboard Principal**: Estadísticas generales y métricas clave
- **Lista de Licitaciones**: Búsqueda, filtrado y paginación
- **Detalle de Licitación**: Vista completa de cada licitación
- **Análisis Avanzado**: Gráficos y análisis por diferentes dimensiones
- **ETL Automático**: Extracción desde múltiples fuentes gubernamentales
- **API REST**: Endpoints completos para todas las funcionalidades

### 🎯 Fuentes de Datos Soportadas

- **ComprasMX** (comprasgob.gob.mx)
- **DOF** (Diario Oficial de la Federación)
- **Sistemas Estatales** (En desarrollo)

### 📱 Interfaz de Usuario

- **Responsive Design**: Optimizado para desktop y móvil
- **Búsqueda Avanzada**: Filtros por múltiples criterios
- **Visualizaciones**: Charts interactivos con datos en tiempo real
- **Paginación**: Manejo eficiente de grandes volúmenes de datos

## 🔧 Problemas Resueltos Recientemente

### ✅ Frontend no hacía queries al backend
**Problema:** El frontend no se podía conectar al backend debido a la falta de configuración del proxy.

**Solución:** Se añadió configuración de proxy en `vite.config.ts`:
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

### ✅ Fechas incorrectas en la tabla de licitaciones
**Problema:** Solo se mostraba fecha de publicación, faltaba fecha de apertura.

**Solución:** Se añadió columna "Fecha Apertura" en la tabla de licitaciones mostrando tanto `fecha_publicacion` como `fecha_apertura`.

### ✅ Manejo de errores mejorado
**Problema:** Errores de conexión no eran claros para el usuario.

**Solución:** Se implementó mejor manejo de errores en el servicio API con mensajes más descriptivos.

## 🏗️ Estructura del Proyecto

```
paloma-licitera-new/
├── frontend/                 # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/       # Componentes reutilizables
│   │   ├── pages/           # Páginas principales
│   │   ├── services/        # API services
│   │   └── types/           # TypeScript types
│   └── package.json
├── src/                     # Backend Python
│   ├── api.py              # FastAPI application
│   ├── database.py         # Database models & operations
│   ├── etl.py              # ETL processes
│   └── extractors/         # Data extractors
├── etl-process/            # ETL configuration
└── start_project.sh        # Quick start script
```

## 📋 API Endpoints

### Principales
- `GET /` - Información de la API
- `GET /stats` - Estadísticas generales
- `GET /licitaciones` - Lista de licitaciones con filtros
- `GET /detalle/{id}` - Detalle de licitación específica
- `GET /filtros` - Filtros disponibles

### Análisis
- `GET /analisis/por-tipo-contratacion` - Análisis por tipo de contratación
- `GET /analisis/por-dependencia` - Análisis por dependencia
- `GET /analisis/por-fuente` - Análisis por fuente
- `GET /analisis/temporal` - Análisis temporal

## 🚨 Solución de Problemas Comunes

### El frontend muestra "Error de conexión"
1. Verificar que el backend esté ejecutándose en http://localhost:8000
2. Verificar que no hay conflictos de puertos
3. Revisar los logs de la consola del navegador

### No aparecen datos en el dashboard
1. Ejecutar el proceso ETL para extraer datos:
```bash
python -m src.etl
```
2. Verificar que la base de datos tenga datos:
```bash
psql -h localhost -U postgres -d paloma_licitera -c "SELECT COUNT(*) FROM licitaciones;"
```

### Errores al instalar dependencias
```bash
# Limpiar cache de npm
cd frontend && npm cache clean --force && npm install

# Reinstalar dependencias de Python
pip install --upgrade -r requirements.txt
```

## 📚 Tecnologías Utilizadas

### Backend
- **FastAPI** - Framework web moderno para Python
- **PostgreSQL** - Base de datos robusta y escalable
- **Pandas** - Manipulación y análisis de datos
- **BeautifulSoup4** - Web scraping
- **Uvicorn** - Servidor ASGI

### Frontend
- **React 18** - Librería de UI
- **TypeScript** - Tipado estático
- **Vite** - Build tool y dev server
- **Tailwind CSS** - Framework de CSS
- **Lucide React** - Iconos
- **Date-fns** - Manipulación de fechas

## 🤝 Contribuir

1. Fork el repositorio
2. Crear una rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit los cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📞 Soporte

Para problemas o preguntas, crear un issue en GitHub o contactar al equipo de desarrollo.

---

**Estado del Proyecto:** ✅ En Desarrollo Activo  
**Última Actualización:** Agosto 2025