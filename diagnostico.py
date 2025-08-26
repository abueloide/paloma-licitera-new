#!/usr/bin/env python3
"""
Script de diagnóstico para Paloma Licitera
==========================================
Verifica conexión a BD, crea tablas si no existen, y muestra estado
"""

import sys
import psycopg2
import yaml
from pathlib import Path

def cargar_config():
    """Cargar configuración"""
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def verificar_bd():
    """Verificar y arreglar base de datos"""
    config = cargar_config()
    db = config['database']
    
    print("🔍 DIAGNÓSTICO DE BASE DE DATOS")
    print("="*50)
    
    # 1. Intentar conectar
    try:
        print(f"📡 Conectando a: {db['host']}:{db['port']}/{db['name']}")
        conn = psycopg2.connect(
            host=db['host'],
            port=db['port'],
            database=db['name'],
            user=db['user'],
            password=db['password']
        )
        print("✅ Conexión exitosa")
    except psycopg2.OperationalError as e:
        print(f"❌ Error de conexión: {e}")
        print("\n🔧 SOLUCIÓN:")
        print(f"1. Crear la base de datos:")
        print(f"   psql -U postgres -c 'CREATE DATABASE {db['name']};'")
        print(f"2. Verificar que PostgreSQL esté corriendo:")
        print(f"   brew services start postgresql  # Mac")
        print(f"   sudo systemctl start postgresql # Linux")
        return False
    
    cursor = conn.cursor()
    
    # 2. Verificar tabla
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'licitaciones'
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM licitaciones;")
            count = cursor.fetchone()[0]
            print(f"✅ Tabla 'licitaciones' existe con {count} registros")
            
            # Estadísticas por fuente
            if count > 0:
                cursor.execute("""
                    SELECT fuente, COUNT(*) 
                    FROM licitaciones 
                    GROUP BY fuente 
                    ORDER BY COUNT(*) DESC;
                """)
                print("\n📊 Registros por fuente:")
                for fuente, cnt in cursor.fetchall():
                    print(f"   - {fuente}: {cnt}")
        else:
            print("⚠️  Tabla 'licitaciones' NO existe")
            print("🔧 Creando tabla...")
            
            # Crear tabla
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licitaciones (
                    id SERIAL PRIMARY KEY,
                    fuente VARCHAR(50) NOT NULL,
                    fecha_publicacion DATE,
                    fecha_limite DATE,
                    titulo TEXT,
                    descripcion TEXT,
                    entidad_compradora VARCHAR(500),
                    entidad_convocante VARCHAR(500),
                    tipo_contratacion VARCHAR(100),
                    tipo_licitacion VARCHAR(100),
                    estado VARCHAR(50),
                    monto_minimo DECIMAL(20,2),
                    monto_maximo DECIMAL(20,2),
                    moneda VARCHAR(10),
                    url TEXT,
                    numero_procedimiento VARCHAR(200),
                    fecha_inicio_vigencia DATE,
                    fecha_fin_vigencia DATE,
                    notas TEXT,
                    archivo_origen VARCHAR(200),
                    datos_originales JSONB,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(fuente, numero_procedimiento)
                );
            """)
            
            # Crear índices
            cursor.execute("CREATE INDEX idx_fuente ON licitaciones(fuente);")
            cursor.execute("CREATE INDEX idx_fecha_publicacion ON licitaciones(fecha_publicacion);")
            cursor.execute("CREATE INDEX idx_entidad ON licitaciones(entidad_compradora);")
            cursor.execute("CREATE INDEX idx_numero ON licitaciones(numero_procedimiento);")
            
            conn.commit()
            print("✅ Tabla creada exitosamente")
            
    except Exception as e:
        print(f"❌ Error con la tabla: {e}")
        conn.rollback()
        return False
    
    # 3. Verificar archivos de datos
    print("\n📁 ARCHIVOS DE DATOS:")
    data_dir = Path("data/raw")
    
    if data_dir.exists():
        for fuente in ['dof', 'comprasmx', 'tianguis']:
            fuente_dir = data_dir / fuente
            if fuente_dir.exists():
                files = list(fuente_dir.glob('*'))
                print(f"   - {fuente}: {len(files)} archivos")
                if files and len(files) <= 3:
                    for f in files[:3]:
                        print(f"     • {f.name}")
    else:
        print("   ❌ No existe directorio data/raw")
        print("   🔧 Creando directorios...")
        for fuente in ['dof', 'comprasmx', 'tianguis']:
            (data_dir / fuente).mkdir(parents=True, exist_ok=True)
        print("   ✅ Directorios creados")
    
    # 4. Test de inserción
    print("\n🧪 TEST DE INSERCIÓN:")
    try:
        cursor.execute("""
            INSERT INTO licitaciones (
                fuente, titulo, descripcion, entidad_compradora, 
                numero_procedimiento, fecha_publicacion
            ) VALUES (
                'TEST', 'Licitación de prueba', 'Test de diagnóstico',
                'Sistema de diagnóstico', 'TEST-001', CURRENT_DATE
            )
            ON CONFLICT (fuente, numero_procedimiento) DO NOTHING;
        """)
        conn.commit()
        print("✅ Inserción de prueba exitosa")
        
        # Limpiar test
        cursor.execute("DELETE FROM licitaciones WHERE fuente = 'TEST';")
        conn.commit()
        print("✅ Limpieza de prueba exitosa")
        
    except Exception as e:
        print(f"❌ Error en test de inserción: {e}")
        conn.rollback()
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("\nSiguientes pasos:")
    print("1. Si hay archivos: ./paloma.sh download-quick")
    print("2. Si no hay archivos: ./paloma.sh download")
    print("3. Iniciar sistema: ./paloma.sh start")
    
    return True

if __name__ == "__main__":
    try:
        verificar_bd()
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        sys.exit(1)
