# GUÍA RÁPIDA DE INSTALACIÓN - PALOMA LICITERA

## 🚀 Instalación Completa (Recomendado)

Si tienes problemas con dependencias faltantes, usa este nuevo script que instala TODO:

```bash
# 1. Clonar el repositorio (si no lo has hecho)
git clone https://github.com/abueloide/paloma-licitera-new.git
cd paloma-licitera-new

# 2. Dar permisos de ejecución al script
chmod +x install_dependencies.sh

# 3. Ejecutar el instalador completo
./install_dependencies.sh

# 4. Iniciar el dashboard
./start_dashboard.sh
```

## 📋 Requisitos Previos

El script verificará automáticamente estos requisitos:

- **Python 3.9+** 
- **Node.js 16+** y npm
- **PostgreSQL** (con base de datos `paloma_licitera`)

## 🗄️ Configuración de Base de Datos

Si no tienes la base de datos configurada:

```bash
# Crear la base de datos
psql -U postgres -c "CREATE DATABASE paloma_licitera;"

# Editar las credenciales en config.yaml
nano config.yaml
```

## 🔧 Qué hace el script `install_dependencies.sh`

1. **Verifica prerequisitos**: Python, Node.js, PostgreSQL
2. **Limpia instalaciones anteriores** (opcional)
3. **Crea entorno virtual Python** nuevo y limpio
4. **Instala TODAS las dependencias Python**:
   - FastAPI, Uvicorn
   - psycopg2, SQLAlchemy
   - Playwright (con navegadores)
   - pandas, requests, BeautifulSoup4
   - Y todas las demás librerías necesarias
5. **Instala TODAS las dependencias del Frontend**:
   - React, TypeScript, Vite
   - Tailwind CSS
   - Todas las librerías de UI (Radix, Shadcn)
   - Axios, React Query, React Router
6. **Verifica la configuración**
7. **Verifica la conexión a PostgreSQL**
8. **Crea directorios necesarios**
9. **Configura permisos de scripts**

## ✅ Verificación de Instalación

El script mostrará checkmarks verdes (✅) para cada componente instalado correctamente:

```
✅ Python 3.11 encontrado
✅ Node.js v18.17.0 encontrado
✅ npm 9.6.7 encontrado
✅ PostgreSQL 15.3 encontrado
✅ uvicorn instalado
✅ fastapi instalado
✅ psycopg2 instalado
✅ pandas instalado
✅ playwright instalado
✅ 250+ paquetes npm instalados
```

## 🚦 Iniciar el Dashboard

Una vez instalado todo:

```bash
# Usar el script principal
./start_dashboard.sh
```

El dashboard estará disponible en:
- **Frontend**: http://localhost:3001
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🛑 Detener el Dashboard

```bash
./stop_dashboard.sh
```

## 🐛 Solución de Problemas

### Error: "No module named 'uvicorn'"
```bash
# Ejecutar el instalador completo
./install_dependencies.sh
```

### Error: "Cannot find module 'react'"
```bash
# Reinstalar dependencias del frontend
cd frontend
rm -rf node_modules package-lock.json
npm install
cd ..
```

### Error: "psycopg2" no instalado
```bash
# Activar el entorno virtual y reinstalar
source venv/bin/activate
pip install psycopg2-binary
```

### Error: Base de datos vacía
```bash
# Ejecutar el proceso ETL para cargar datos
source venv/bin/activate
python src/etl.py --all
```

## 📁 Estructura del Proyecto

```
paloma-licitera-new/
├── install_dependencies.sh  # ← NUEVO: Instalador completo
├── start_dashboard.sh       # Script de inicio principal
├── stop_dashboard.sh        # Script para detener
├── config.yaml             # Configuración de BD
├── requirements.txt        # Dependencias Python
├── venv/                   # Entorno virtual Python (se crea)
├── src/
│   ├── api.py             # API FastAPI principal
│   ├── database.py        # Conexión a PostgreSQL
│   └── etl.py             # Proceso ETL
├── frontend/
│   ├── package.json       # Dependencias Node.js
│   ├── node_modules/      # Módulos npm (se crea)
│   └── src/               # Código React
└── logs/                  # Logs de la aplicación (se crea)
```

## 💡 Tips

- **Siempre usa el entorno virtual**: El script lo activa automáticamente
- **Revisa los logs** si algo falla: `tail -f logs/backend.log` o `logs/frontend.log`
- **PostgreSQL debe estar corriendo** antes de iniciar el dashboard
- **El proceso es idempotente**: Puedes ejecutar el instalador varias veces sin problemas

## 🆘 Soporte

Si sigues teniendo problemas después de ejecutar `install_dependencies.sh`:

1. Revisa que PostgreSQL esté ejecutándose
2. Verifica las credenciales en `config.yaml`
3. Revisa los logs en la carpeta `logs/`
4. Asegúrate de tener permisos de escritura en el directorio

---

**¡Con el nuevo script `install_dependencies.sh`, todos los problemas de dependencias deberían resolverse automáticamente!** 🎉
