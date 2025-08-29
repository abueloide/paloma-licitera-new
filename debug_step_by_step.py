#!/usr/bin/env python3
"""
SCRIPT DE DEBUG - Analizar paso a paso qué está fallando
"""

import json
import sys
from pathlib import Path

# Agregar paths
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_archivos_generados():
    """Ver exactamente qué archivos genera el script de prueba"""
    print("🔍 ANALIZANDO ARCHIVOS DE PRUEBA GENERADOS...")
    
    test_dir = Path("data/raw/comprasmx_test")
    
    if not test_dir.exists():
        print("❌ Directorio de prueba no existe")
        return
    
    print(f"\n📁 Contenido de {test_dir}:")
    for archivo in test_dir.iterdir():
        print(f"  - {archivo.name}")
        if archivo.suffix == '.json':
            with open(archivo, 'r') as f:
                data = json.load(f)
            print(f"    Tipo: {type(data)}")
            if isinstance(data, dict):
                print(f"    Claves: {list(data.keys())}")
                if 'expedientes' in data:
                    print(f"    Expedientes: {len(data['expedientes'])}")
                    for i, exp in enumerate(data['expedientes'][:2]):
                        print(f"      [{i}] Claves: {list(exp.keys())}")
    
    detalles_dir = test_dir / "detalles"
    if detalles_dir.exists():
        print(f"\n📁 Contenido de {detalles_dir}:")
        for archivo in detalles_dir.iterdir():
            print(f"  - {archivo.name}")
            if archivo.suffix == '.json':
                with open(archivo, 'r') as f:
                    data = json.load(f)
                print(f"    codigo_expediente: {data.get('codigo_expediente')}")

def debug_extractor_paso_a_paso():
    """Debugear el extractor paso a paso"""
    print("\n🔍 DEBUGGING EXTRACTOR PASO A PASO...")
    
    # Importar y configurar
    import yaml
    from extractors.comprasmx import ComprasMXExtractor
    import logging
    
    # Configurar logging para ver todo
    logging.basicConfig(level=logging.DEBUG)
    
    test_dir = Path("data/raw/comprasmx_test")
    
    if not test_dir.exists():
        print("❌ Directorio de prueba no existe - ejecuta test_end_to_end.py primero")
        return
    
    # Crear extractor
    config_test = {
        'paths': {'data_raw': str(test_dir.parent)},
        'sources': {'comprasmx': {'enabled': True}}
    }
    
    extractor = ComprasMXExtractor(config_test)
    extractor.data_dir = test_dir
    
    print(f"📂 Data dir: {extractor.data_dir}")
    print(f"📂 Carpeta detalles: {extractor.carpeta_detalles}")
    
    # 1. Verificar si encuentra archivos
    json_files = list(extractor.data_dir.glob("*.json"))
    print(f"📄 Archivos JSON encontrados: {len(json_files)}")
    for f in json_files:
        print(f"  - {f.name}")
    
    # 2. Verificar si encuentra detalles
    if extractor.carpeta_detalles.exists():
        detalles_files = list(extractor.carpeta_detalles.glob("detalle_*.json"))
        print(f"📄 Archivos de detalles encontrados: {len(detalles_files)}")
        for f in detalles_files:
            print(f"  - {f.name}")
    else:
        print("❌ Carpeta de detalles no existe")
    
    # 3. Intentar cargar detalles
    try:
        if extractor.carpeta_detalles.exists():
            extractor._cargar_detalles_individuales()
        print(f"✅ Detalles cargados en memoria: {len(extractor.detalles_cargados)}")
        for codigo, detalle in extractor.detalles_cargados.items():
            print(f"  - {codigo}: {detalle.get('codigo_expediente')}")
    except Exception as e:
        print(f"❌ Error cargando detalles: {e}")
    
    # 4. Procesar un archivo específico
    if json_files:
        archivo_test = json_files[0]
        print(f"\n🔄 Procesando archivo: {archivo_test.name}")
        
        try:
            licitaciones = extractor._procesar_json(archivo_test)
            print(f"✅ Licitaciones procesadas: {len(licitaciones)}")
            
            for i, lic in enumerate(licitaciones):
                print(f"\n📄 Licitación {i+1}:")
                print(f"  numero_procedimiento: {lic.get('numero_procedimiento')}")
                print(f"  titulo: {lic.get('titulo')}")
                print(f"  url_original: {lic.get('url_original')}")
                print(f"  descripcion (chars): {len(lic.get('descripcion', ''))}")
                print(f"  datos_especificos: {type(lic.get('datos_especificos'))}")
                
                if isinstance(lic.get('datos_especificos'), dict):
                    datos_esp = lic['datos_especificos']
                    print(f"  datos_especificos.keys: {list(datos_esp.keys())}")
                    if 'detalle_individual' in datos_esp:
                        print(f"  ✅ TIENE detalle_individual")
                        detalle = datos_esp['detalle_individual']
                        print(f"    url_completa_hash: {detalle.get('url_completa_hash')}")
                    else:
                        print(f"  ❌ NO tiene detalle_individual")
                
        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")
            import traceback
            traceback.print_exc()

def crear_datos_de_prueba_simples():
    """Crear datos de prueba más simples para debugging"""
    print("\n🧪 CREANDO DATOS DE PRUEBA SIMPLES...")
    
    # Crear directorio de prueba
    test_dir = Path("data/raw/comprasmx_debug")
    detalles_dir = test_dir / "detalles"
    detalles_dir.mkdir(parents=True, exist_ok=True)
    
    # Datos súper simples
    expedientes_test = {
        "fecha_captura": "2025-08-29",
        "total_expedientes": 1,
        "expedientes": [
            {
                "cod_expediente": "DEBUG001",
                "nombre_procedimiento": "Debug Test 1",
                "descripcion": "Desc básica",
                "siglas": "DEBUG"
            }
        ]
    }
    
    # Guardar archivo principal
    with open(test_dir / "todos_expedientes_debug.json", 'w', encoding='utf-8') as f:
        json.dump(expedientes_test, f, ensure_ascii=False, indent=2)
    
    # Detalle individual súper simple
    detalle1 = {
        "codigo_expediente": "DEBUG001",
        "url_completa_con_hash": "https://debug.test.gob.mx/DEBUG001#hash999",
        "informacion_extraida": {
            "descripcion_completa": "Descripción súper detallada desde el detalle individual con mucho más texto que la original."
        }
    }
    
    # Guardar detalle
    with open(detalles_dir / "detalle_DEBUG001.json", 'w', encoding='utf-8') as f:
        json.dump(detalle1, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Datos de debug creados en: {test_dir}")
    
    return test_dir

def main():
    print("🔍 ANÁLISIS PASO A PASO DEL PROBLEMA")
    print("=" * 60)
    
    # Opción 1: Analizar archivos existentes del test anterior
    debug_archivos_generados()
    debug_extractor_paso_a_paso()
    
    # Opción 2: Crear datos más simples y probar
    print("\n" + "=" * 60)
    print("🧪 PROBANDO CON DATOS MÁS SIMPLES")
    
    test_dir_debug = crear_datos_de_prueba_simples()
    
    # Probar extractor con datos simples
    try:
        import yaml
        from extractors.comprasmx import ComprasMXExtractor
        
        config_test = {
            'paths': {'data_raw': str(test_dir_debug.parent)},
            'sources': {'comprasmx': {'enabled': True}}
        }
        
        extractor = ComprasMXExtractor(config_test)
        extractor.data_dir = test_dir_debug
        
        print(f"\n🔄 Probando con datos debug...")
        licitaciones = extractor.extraer()
        
        print(f"📊 Resultado: {len(licitaciones)} licitaciones")
        
        if len(licitaciones) > 0:
            lic = licitaciones[0]
            print(f"\n📄 Análisis de licitación DEBUG001:")
            print(f"  numero_procedimiento: '{lic.get('numero_procedimiento')}'")
            print(f"  url_original: '{lic.get('url_original')}'")
            print(f"  descripcion: '{lic.get('descripcion')}'")
            print(f"  datos_especificos type: {type(lic.get('datos_especificos'))}")
            
            if lic.get('datos_especificos'):
                datos_esp = lic['datos_especificos']
                if isinstance(datos_esp, dict):
                    print(f"  datos_especificos.keys: {list(datos_esp.keys())}")
                    if 'detalle_individual' in datos_esp:
                        print("  ✅ TIENE detalle_individual!")
                        detalle = datos_esp['detalle_individual']
                        print(f"    URL hash: {detalle.get('url_completa_hash')}")
                        print(f"    Desc completa chars: {len(str(detalle.get('descripcion_completa', '')))}")
                    else:
                        print("  ❌ NO tiene detalle_individual")
                else:
                    print(f"  ❌ datos_especificos no es dict: {datos_esp}")
            else:
                print("  ❌ NO tiene datos_especificos")
        
        # Limpiar
        import shutil
        if test_dir_debug.exists():
            shutil.rmtree(test_dir_debug)
            print(f"\n🧹 Datos debug limpiados")
    
    except Exception as e:
        print(f"❌ Error en prueba debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
