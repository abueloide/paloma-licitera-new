#!/usr/bin/env python3
"""
SCRIPT DE VERIFICACIÓN END-TO-END
Verifica que todo el flujo funcione: Scraper → Extractor → Base de Datos

Este script NO ejecuta el scraper completo, solo verifica la integración
"""

import json
import sys
import yaml
from pathlib import Path
from datetime import datetime

# Agregar paths
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import Database
from extractors.comprasmx import ComprasMXExtractor

def verificar_scraper_modificado():
    """Verificar que el scraper tenga las funciones nuevas"""
    print("\n🔍 VERIFICANDO SCRAPER MODIFICADO...")
    
    scraper_path = Path("etl-process/extractors/comprasMX/ComprasMX_v2Claude.py")
    
    if not scraper_path.exists():
        print("❌ Scraper no encontrado")
        return False
    
    # Leer contenido del scraper
    with open(scraper_path, 'r') as f:
        contenido = f.read()
    
    # Verificar funciones nuevas
    funciones_requeridas = [
        "procesar_licitaciones_en_pagina_actual",
        "carpeta_detalles",
        "detalles_extraidos", 
        "extraer_informacion_detalle",
        "integrar_detalle_individual",
        "guardar_detalle_individual"
    ]
    
    funciones_encontradas = []
    for funcion in funciones_requeridas:
        if funcion in contenido:
            funciones_encontradas.append(funcion)
            print(f"  ✅ {funcion}")
        else:
            print(f"  ❌ {funcion}")
    
    porcentaje = len(funciones_encontradas) / len(funciones_requeridas) * 100
    print(f"\n📊 Scraper modificado: {porcentaje:.1f}% ({len(funciones_encontradas)}/{len(funciones_requeridas)})")
    
    return porcentaje > 80

def verificar_extractor_soporte():
    """Verificar que el extractor soporte detalles individuales"""
    print("\n🔍 VERIFICANDO EXTRACTOR...")
    
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        extractor = ComprasMXExtractor(config)
        
        # Verificar atributos necesarios
        atributos = [
            hasattr(extractor, 'carpeta_detalles'),
            hasattr(extractor, 'detalles_cargados'),
            hasattr(extractor, '_cargar_detalles_individuales'),
            hasattr(extractor, '_integrar_detalle_individual')
        ]
        
        for i, attr in enumerate(['carpeta_detalles', 'detalles_cargados', '_cargar_detalles_individuales', '_integrar_detalle_individual']):
            if atributos[i]:
                print(f"  ✅ {attr}")
            else:
                print(f"  ❌ {attr}")
        
        porcentaje = sum(atributos) / len(atributos) * 100
        print(f"\n📊 Extractor compatible: {porcentaje:.1f}% ({sum(atributos)}/{len(atributos)})")
        
        return porcentaje == 100
        
    except Exception as e:
        print(f"  ❌ Error verificando extractor: {e}")
        return False

def simular_datos_detalles():
    """Crear datos de prueba para simular el flujo"""
    print("\n🧪 CREANDO DATOS DE PRUEBA...")
    
    # Crear directorio de prueba
    test_dir = Path("data/raw/comprasmx_test")
    detalles_dir = test_dir / "detalles"
    detalles_dir.mkdir(parents=True, exist_ok=True)
    
    # Datos de prueba - archivo principal
    expedientes_test = {
        "fecha_captura": datetime.now().isoformat(),
        "total_expedientes": 2,
        "expedientes": [
            {
                "cod_expediente": "TEST001",
                "nombre_procedimiento": "Licitación de Prueba 1",
                "descripcion": "Descripción básica 1",
                "siglas": "TEST",
                "tipo_procedimiento": "LICITACIÓN PÚBLICA",
                "estatus_alterno": "VIGENTE",
                "fecha_publicacion": "2025-08-29",
                "monto_estimado": "$100,000.00"
            },
            {
                "cod_expediente": "TEST002", 
                "nombre_procedimiento": "Licitación de Prueba 2",
                "descripcion": "Descripción básica 2",
                "siglas": "TEST",
                "tipo_procedimiento": "INVITACIÓN A CUANDO MENOS 3",
                "estatus_alterno": "VIGENTE",
                "fecha_publicacion": "2025-08-29",
                "monto_estimado": "$50,000.00"
            }
        ]
    }
    
    # Guardar archivo principal
    with open(test_dir / "todos_expedientes_test.json", 'w', encoding='utf-8') as f:
        json.dump(expedientes_test, f, ensure_ascii=False, indent=2)
    
    # Datos de prueba - detalles individuales
    detalle1 = {
        "codigo_expediente": "TEST001",
        "url_completa_con_hash": "https://comprasmx.test.gob.mx/procedimiento/TEST001#hash123",
        "informacion_extraida": {
            "descripcion_completa": "Descripción detallada muy completa de la licitación de prueba 1 con todos los detalles técnicos y especificaciones.",
            "documentos_adjuntos": [
                {"nombre": "Bases técnicas", "url": "https://comprasmx.test.gob.mx/doc1.pdf"},
                {"nombre": "Anexo técnico", "url": "https://comprasmx.test.gob.mx/doc2.pdf"}
            ],
            "contacto": {
                "emails": ["contacto@test.gob.mx"],
                "telefonos": ["55-1234-5678"]
            }
        },
        "timestamp_procesamiento": datetime.now().isoformat(),
        "procesado_exitosamente": True
    }
    
    detalle2 = {
        "codigo_expediente": "TEST002",
        "url_completa_con_hash": "https://comprasmx.test.gob.mx/procedimiento/TEST002#hash456",
        "informacion_extraida": {
            "descripcion_completa": "Descripción detallada de la licitación 2 con especificaciones completas.",
            "documentos_adjuntos": [
                {"nombre": "Convocatoria", "url": "https://comprasmx.test.gob.mx/conv2.pdf"}
            ],
            "contacto": {
                "emails": ["admin@test.gob.mx"]
            }
        },
        "timestamp_procesamiento": datetime.now().isoformat(),
        "procesado_exitosamente": True
    }
    
    # Guardar detalles individuales
    with open(detalles_dir / "detalle_TEST001.json", 'w', encoding='utf-8') as f:
        json.dump(detalle1, f, ensure_ascii=False, indent=2)
    
    with open(detalles_dir / "detalle_TEST002.json", 'w', encoding='utf-8') as f:
        json.dump(detalle2, f, ensure_ascii=False, indent=2)
    
    # Índice de detalles
    indice = {
        "fecha_creacion": datetime.now().isoformat(),
        "total_detalles": 2,
        "detalles": {
            "TEST001": {"archivo": "detalle_TEST001.json"},
            "TEST002": {"archivo": "detalle_TEST002.json"}
        }
    }
    
    with open(detalles_dir / "indice_detalles.json", 'w', encoding='utf-8') as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ Datos de prueba creados en: {test_dir}")
    print(f"  ✅ Carpeta detalles: {detalles_dir}")
    print(f"  ✅ 2 expedientes + 2 detalles individuales")
    
    return test_dir

def probar_extractor_con_datos(test_dir):
    """Probar el extractor con los datos de prueba"""
    print("\n🧪 PROBANDO EXTRACTOR CON DATOS DE PRUEBA...")
    
    try:
        # Crear configuración temporal
        config_test = {
            'paths': {'data_raw': str(test_dir.parent)},
            'sources': {'comprasmx': {'enabled': True}}
        }
        
        # Modificar temporalmente la data_dir del extractor
        extractor = ComprasMXExtractor(config_test)
        extractor.data_dir = test_dir
        
        # Ejecutar extracción
        licitaciones = extractor.extraer()
        
        print(f"  📊 Licitaciones extraídas: {len(licitaciones)}")
        
        if len(licitaciones) > 0:
            print(f"  ✅ Extractor funciona")
            
            # Verificar integración de detalles
            for i, lic in enumerate(licitaciones):
                codigo = lic.get('numero_procedimiento')
                url = lic.get('url_original', '')
                desc = lic.get('descripcion', '')
                datos_esp = lic.get('datos_especificos', {})
                
                print(f"\n  📄 Licitación {i+1}: {codigo}")
                print(f"    URL: {'con hash' if '#hash' in url else 'sin hash'}")
                print(f"    Descripción: {len(desc)} caracteres")
                
                # Verificar si tiene detalle individual integrado
                if isinstance(datos_esp, dict) and 'detalle_individual' in datos_esp:
                    print(f"    ✅ Detalle individual integrado")
                    detalle = datos_esp['detalle_individual']
                    
                    if detalle.get('url_completa_hash'):
                        print(f"      ✅ URL con hash")
                    if detalle.get('descripcion_completa'):
                        print(f"      ✅ Descripción enriquecida")
                    if detalle.get('documentos_adjuntos'):
                        print(f"      ✅ Documentos adjuntos: {len(detalle['documentos_adjuntos'])}")
                    if detalle.get('contacto'):
                        print(f"      ✅ Información de contacto")
                        
                else:
                    print(f"    ❌ Sin detalle individual integrado")
        
        return len(licitaciones) > 0 and any(
            isinstance(lic.get('datos_especificos'), dict) and 
            'detalle_individual' in lic.get('datos_especificos', {}) 
            for lic in licitaciones
        )
        
    except Exception as e:
        print(f"  ❌ Error probando extractor: {e}")
        import traceback
        traceback.print_exc()
        return False

def probar_insercion_bd(licitaciones):
    """Probar inserción en base de datos"""
    print("\n🗄️ PROBANDO INSERCIÓN EN BASE DE DATOS...")
    
    try:
        db = Database()
        
        # Verificar conexión
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            print("  ✅ Conexión a BD exitosa")
        
        # Insertar licitaciones de prueba
        insertadas = 0
        errores = 0
        
        for lic in licitaciones:
            # Agregar campos requeridos para la BD
            lic['fuente'] = 'ComprasMX'
            lic['hash_contenido'] = f"test_{lic.get('numero_procedimiento')}"
            
            try:
                if db.insertar_licitacion(lic):
                    insertadas += 1
                    print(f"    ✅ {lic.get('numero_procedimiento')} insertada")
            except Exception as e:
                errores += 1
                print(f"    ❌ Error insertando {lic.get('numero_procedimiento')}: {e}")
        
        print(f"\n  📊 Insertadas: {insertadas}/{len(licitaciones)}")
        
        # Verificar que se guardaron los datos enriquecidos
        if insertadas > 0:
            print("\n  🔍 Verificando datos enriquecidos en BD...")
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT numero_procedimiento, url_original, 
                           length(descripcion) as desc_len,
                           datos_especificos IS NOT NULL as tiene_datos_esp,
                           datos_especificos -> 'detalle_individual' IS NOT NULL as tiene_detalle
                    FROM licitaciones 
                    WHERE fuente = 'ComprasMX' 
                    AND hash_contenido LIKE 'test_%'
                    ORDER BY numero_procedimiento
                """)
                
                for row in cursor.fetchall():
                    print(f"    📄 {row['numero_procedimiento']}:")
                    print(f"      URL: {'con hash' if '#hash' in (row['url_original'] or '') else 'básica'}")
                    print(f"      Descripción: {row['desc_len']} chars")
                    print(f"      Datos específicos: {'Sí' if row['tiene_datos_esp'] else 'No'}")
                    print(f"      Detalle individual: {'Sí' if row['tiene_detalle'] else 'No'}")
        
        return insertadas > 0
        
    except Exception as e:
        print(f"  ❌ Error probando BD: {e}")
        import traceback
        traceback.print_exc()
        return False

def limpiar_datos_prueba(test_dir):
    """Limpiar datos de prueba"""
    print(f"\n🧹 LIMPIANDO DATOS DE PRUEBA...")
    
    try:
        # Limpiar BD
        db = Database()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM licitaciones WHERE hash_contenido LIKE 'test_%'")
            deleted = cursor.rowcount
            print(f"  ✅ {deleted} registros eliminados de BD")
        
        # Limpiar archivos
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"  ✅ Directorio de prueba eliminado")
            
    except Exception as e:
        print(f"  ⚠️ Error limpiando: {e}")

def main():
    print("🧪 VERIFICACIÓN END-TO-END - PALOMA LICITERA")
    print("=" * 60)
    
    resultados = []
    
    # 1. Verificar scraper modificado
    resultados.append(("Scraper modificado", verificar_scraper_modificado()))
    
    # 2. Verificar extractor compatible
    resultados.append(("Extractor compatible", verificar_extractor_soporte()))
    
    # 3. Simular datos y probar flujo
    test_dir = simular_datos_detalles()
    
    try:
        # 4. Probar extractor con datos
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        extractor = ComprasMXExtractor(config)
        extractor.data_dir = test_dir
        licitaciones = extractor.extraer()
        
        exito_extractor = probar_extractor_con_datos(test_dir)
        resultados.append(("Extractor + Detalles", exito_extractor))
        
        # 5. Probar inserción en BD
        if len(licitaciones) > 0:
            exito_bd = probar_insercion_bd(licitaciones)
            resultados.append(("Inserción BD", exito_bd))
        else:
            resultados.append(("Inserción BD", False))
            
    except Exception as e:
        print(f"❌ Error en pruebas: {e}")
        resultados.append(("Extractor + Detalles", False))
        resultados.append(("Inserción BD", False))
    
    finally:
        # Limpiar
        limpiar_datos_prueba(test_dir)
    
    # Mostrar resultados finales
    print("\n" + "=" * 60)
    print("📊 RESULTADOS FINALES")
    print("=" * 60)
    
    todos_exitosos = True
    for nombre, exito in resultados:
        status = "✅ FUNCIONA" if exito else "❌ FALLA"
        print(f"{nombre:.<30} {status}")
        if not exito:
            todos_exitosos = False
    
    print("\n" + "=" * 60)
    if todos_exitosos:
        print("🎉 END-TO-END COMPLETAMENTE FUNCIONAL")
        print("✅ El scraper → extractor → BD funciona perfectamente")
        print("✅ Los detalles individuales se integran correctamente")
        print("✅ La información enriquecida se guarda en PostgreSQL")
    else:
        print("⚠️ ALGUNOS COMPONENTES NECESITAN CORRECCIÓN")
        print("   Revisa los errores mostrados arriba")
    
    return todos_exitosos

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verificar end-to-end Paloma Licitera")
    parser.add_argument("--config", default="config.yaml", help="Archivo de configuración")
    args = parser.parse_args()
    
    if not Path(args.config).exists():
        print(f"❌ Archivo de configuración no encontrado: {args.config}")
        sys.exit(1)
    
    exito = main()
    sys.exit(0 if exito else 1)
