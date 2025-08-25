#!/bin/bash

# Script para iniciar el dashboard de Paloma Licitera

echo "🐦 Iniciando Paloma Licitera Dashboard..."

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi

# Verificar si Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado"
    exit 1
fi

# Crear directorio para logs si no existe
mkdir -p logs

# Función para verificar si un puerto está en uso
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  El puerto $1 está en uso"
        return 1
    else
        return 0
    fi
}

# Verificar puertos
if ! check_port 8000; then
    echo "   Si el proceso anterior es de este proyecto, continuando..."
fi

if ! check_port 3001; then
    echo "   Si el proceso anterior es de este proyecto, continuando..."
fi

echo ""
echo "📦 Instalando dependencias del backend..."
pip install -r requirements.txt

echo ""
echo "📦 Instalando dependencias del frontend..."
cd frontend
npm install
cd ..

echo ""
echo "🗄️  Verificando base de datos SQLite..."
if [ ! -f "licitaciones.db" ]; then
    echo "   Creando base de datos SQLite..."
    python3 -c "
import sqlite3
import os
import sys

# Crear la base de datos SQLite
db_path = 'licitaciones.db'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tabla de licitaciones
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS licitaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_procedimiento TEXT NOT NULL,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        entidad_compradora TEXT,
        unidad_compradora TEXT,
        tipo_procedimiento TEXT,
        tipo_contratacion TEXT,
        estado TEXT,
        fecha_publicacion TEXT,
        fecha_apertura TEXT,
        fecha_fallo TEXT,
        monto_estimado REAL,
        moneda TEXT DEFAULT 'MXN',
        fuente TEXT NOT NULL,
        url_original TEXT,
        fecha_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        hash_contenido TEXT UNIQUE
    )''')
    
    # Crear índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_numero_procedimiento ON licitaciones(numero_procedimiento)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entidad ON licitaciones(entidad_compradora)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fecha_pub ON licitaciones(fecha_publicacion)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fuente ON licitaciones(fuente)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_estado ON licitaciones(estado)')
    
    conn.commit()
    conn.close()
    print('   ✅ Base de datos SQLite creada con éxito')
    
except Exception as e:
    print(f'   ❌ Error creando base de datos: {e}')
    sys.exit(1)
    "
    
    # Insertar algunos datos de prueba si la BD está vacía
    python3 -c "
import sqlite3
import random
from datetime import datetime, timedelta

try:
    conn = sqlite3.connect('licitaciones.db')
    cursor = conn.cursor()
    
    # Verificar si ya hay datos
    cursor.execute('SELECT COUNT(*) FROM licitaciones')
    count = cursor.fetchone()[0]
    
    if count == 0:
        print('   📝 Insertando datos de prueba...')
        
        # Datos de prueba
        sample_data = [
            {
                'numero_procedimiento': 'LP-001-2025',
                'titulo': 'Adquisición de equipos de cómputo',
                'descripcion': 'Compra de laptops y equipos de oficina',
                'entidad_compradora': 'Secretaría de Educación Pública',
                'tipo_contratacion': 'ADQUISICIONES',
                'estado': 'VIGENTE',
                'fecha_publicacion': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
                'fecha_apertura': (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d'),
                'monto_estimado': 1500000,
                'fuente': 'COMPRASMX',
                'hash_contenido': 'hash001'
            },
            {
                'numero_procedimiento': 'LP-002-2025',
                'titulo': 'Servicios de limpieza',
                'descripcion': 'Contratación de servicios de limpieza para edificios públicos',
                'entidad_compradora': 'Secretaría de Salud',
                'tipo_contratacion': 'SERVICIOS',
                'estado': 'ABIERTA',
                'fecha_publicacion': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'fecha_apertura': (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
                'monto_estimado': 800000,
                'fuente': 'DOF',
                'hash_contenido': 'hash002'
            },
            {
                'numero_procedimiento': 'LP-003-2025',
                'titulo': 'Obra pública - Construcción de escuela',
                'descripcion': 'Construcción de centro educativo en zona rural',
                'entidad_compradora': 'Gobierno del Estado',
                'tipo_contratacion': 'OBRA_PUBLICA',
                'estado': 'CERRADA',
                'fecha_publicacion': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                'fecha_apertura': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
                'monto_estimado': 5000000,
                'fuente': 'TIANGUIS',
                'hash_contenido': 'hash003'
            }
        ]
        
        for data in sample_data:
            cursor.execute('''
                INSERT INTO licitaciones (
                    numero_procedimiento, titulo, descripcion, entidad_compradora,
                    tipo_contratacion, estado, fecha_publicacion, fecha_apertura,
                    monto_estimado, fuente, hash_contenido
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['numero_procedimiento'], data['titulo'], data['descripcion'],
                data['entidad_compradora'], data['tipo_contratacion'], data['estado'],
                data['fecha_publicacion'], data['fecha_apertura'], data['monto_estimado'],
                data['fuente'], data['hash_contenido']
            ))
        
        conn.commit()
        print('   ✅ Datos de prueba insertados')
    else:
        print(f'   ℹ️  Base de datos ya contiene {count} registros')
    
    conn.close()
    
except Exception as e:
    print(f'   ⚠️  Error insertando datos de prueba: {e}')
    "
    
else
    echo "   ✅ Base de datos SQLite encontrada"
fi

echo ""
echo "🚀 Iniciando servicios..."

# Iniciar backend en segundo plano
echo "   📡 Iniciando backend API (puerto 8000)..."
cd src
python3 -m uvicorn api_sqlite:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Esperar un poco para que el backend se inicie
sleep 3

# Verificar si el backend se inició correctamente
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "   ✅ Backend iniciado (PID: $BACKEND_PID)"
else
    echo "   ❌ Error al iniciar el backend"
    echo "   Ver logs en: logs/backend.log"
    cat logs/backend.log
    exit 1
fi

# Iniciar frontend en segundo plano  
echo "   🎨 Iniciando frontend (puerto 3001)..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Esperar un poco para que el frontend se inicie
sleep 5

# Verificar si el frontend se inició correctamente
if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo "   ✅ Frontend iniciado (PID: $FRONTEND_PID)"
else
    echo "   ❌ Error al iniciar el frontend"
    echo "   Ver logs en: logs/frontend.log"
    echo "   Primeras líneas del log:"
    head -20 logs/frontend.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✨ ¡Dashboard iniciado correctamente!"
echo ""
echo "📊 Dashboard: http://localhost:3001"
echo "📡 API:       http://localhost:8000"
echo ""
echo "📋 Para ver logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "⏹️  Para detener los servicios:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Guardar PIDs para poder detenerlos después
echo "BACKEND_PID=$BACKEND_PID" > .pids
echo "FRONTEND_PID=$FRONTEND_PID" >> .pids

echo "ℹ️  Los servicios están ejecutándose en segundo plano."
echo "   Presiona Ctrl+C para detenerlos, o ejecuta:"
echo "   ./stop_dashboard.sh"

# Mantener el script corriendo para poder detener con Ctrl+C
trap 'echo ""; echo "🛑 Deteniendo servicios..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .pids; echo "✅ Servicios detenidos"; exit 0' INT

# Mostrar URL y esperar
echo ""
echo "🌐 Abriendo dashboard en el navegador..."
sleep 2

# Intentar abrir el navegador (funciona en la mayoría de sistemas)
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:3001 >/dev/null 2>&1
elif command -v open > /dev/null 2>&1; then
    open http://localhost:3001 >/dev/null 2>&1
fi

# Esperar indefinidamente
while true; do
    sleep 1
done