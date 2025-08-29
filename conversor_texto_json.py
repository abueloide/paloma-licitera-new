#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONVERSOR DE TEXTO A JSON - ComprasMX
Convierte el texto copiado de ComprasMX a archivos JSON válidos
"""

import json
import re
from datetime import datetime
from pathlib import Path

def extraer_informacion_comprasmx(texto):
    """Extraer información del texto copiado de ComprasMX"""
    
    # Buscar información específica usando patrones
    info = {}
    
    # Código del expediente
    match = re.search(r'Código del expediente:\s*([A-Z0-9\-]+)', texto)
    if match:
        info['codigo_expediente'] = match.group(1).strip()
    
    # Número de procedimiento
    match = re.search(r'Número de procedimiento de contratación:\s*([A-Z0-9\-]+)', texto)
    if match:
        info['numero_procedimiento'] = match.group(1).strip()
    
    # Estatus
    match = re.search(r'Estatus del procedimiento de contratación:\s*(\w+)', texto)
    if match:
        info['estatus'] = match.group(1).strip()
    
    # Nombre del procedimiento
    match = re.search(r'Nombre del procedimiento de contratación:\s*([^\n]+)', texto)
    if match:
        info['nombre_procedimiento'] = match.group(1).strip()
    
    # Descripción detallada
    match = re.search(r'Descripción detallada del procedimiento de contratación:\s*([^\n]+)', texto)
    if match:
        info['descripcion_completa'] = match.group(1).strip()
    
    # Dependencia o Entidad
    match = re.search(r'Dependencia o Entidad:\s*([^\n]+)', texto)
    if match:
        info['dependencia_entidad'] = match.group(1).strip()
    
    # Ramo
    match = re.search(r'Ramo:\s*([^\n]+)', texto)
    if match:
        info['ramo'] = match.group(1).strip()
    
    # Unidad compradora
    match = re.search(r'Unidad compradora:\s*([^\n]+)', texto)
    if match:
        info['unidad_compradora'] = match.group(1).strip()
    
    # Responsable de la captura
    match = re.search(r'Responsable de la captura:\s*([^\n]+)', texto)
    if match:
        info['responsable_captura'] = match.group(1).strip()
    
    # Correo electrónico
    match = re.search(r'Correo electrónico unidad compradora:\s*([^\s\n]+)', texto)
    if match:
        info['correo_electronico'] = match.group(1).strip()
    
    # Tipo de procedimiento
    match = re.search(r'Tipo de procedimiento de contratación:\s*([^\n]+)', texto)
    if match:
        info['tipo_procedimiento'] = match.group(1).strip()
    
    # Tipo de contratación
    match = re.search(r'Tipo de contratación:\s*([^\n]+)', texto)
    if match:
        info['tipo_contratacion'] = match.group(1).strip()
    
    # Entidad Federativa
    match = re.search(r'Entidad Federativa donde se llevará a cabo la contratación:\s*([^\n]+)', texto)
    if match:
        info['entidad_federativa'] = match.group(1).strip()
    
    # Fechas importantes
    match = re.search(r'Fecha y hora de presentación y apertura de proposiciones:\s*([^\n]+)', texto)
    if match:
        info['fecha_apertura'] = match.group(1).strip()
    
    match = re.search(r'Fecha y hora de junta de aclaraciones:\s*([^\n]+)', texto)
    if match:
        info['fecha_aclaraciones'] = match.group(1).strip()
    
    match = re.search(r'Fecha y hora del acto del Fallo:\s*([^\n]+)', texto)
    if match:
        info['fecha_fallo'] = match.group(1).strip()
    
    # Carácter
    match = re.search(r'Carácter:\s*([^\n]+)', texto)
    if match:
        info['caracter'] = match.group(1).strip()
    
    # Referencia
    match = re.search(r'Referencia / Número de control interno:\s*([^\n]+)', texto)
    if match:
        info['referencia_control'] = match.group(1).strip()
    
    return info

def crear_detalle_json(info, url=""):
    """Crear estructura JSON compatible con el extractor"""
    
    codigo = info.get('codigo_expediente', f'MANUAL_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    
    detalle = {
        'codigo_expediente': codigo,
        'url_completa_con_hash': url or f'https://comprasmx.buengobierno.gob.mx/sitiopublico/#/detalle/{codigo}',
        'timestamp_procesamiento': datetime.now().isoformat(),
        'pagina_origen': 'ComprasMX - Conversión Manual',
        'procesado_exitosamente': True,
        'informacion_extraida': {
            'numero_procedimiento': info.get('numero_procedimiento'),
            'estatus': info.get('estatus'),
            'descripcion_completa': info.get('descripcion_completa'),
            'nombre_procedimiento': info.get('nombre_procedimiento'),
            'dependencia_entidad': info.get('dependencia_entidad'),
            'ramo': info.get('ramo'),
            'unidad_compradora': info.get('unidad_compradora'),
            'responsable_captura': info.get('responsable_captura'),
            'correo_electronico': info.get('correo_electronico'),
            'tipo_procedimiento': info.get('tipo_procedimiento'),
            'tipo_contratacion': info.get('tipo_contratacion'),
            'entidad_federativa': info.get('entidad_federativa'),
            'referencia_control': info.get('referencia_control'),
            'caracter': info.get('caracter'),
            'fechas_detalladas': {
                'apertura_proposiciones': info.get('fecha_apertura'),
                'junta_aclaraciones': info.get('fecha_aclaraciones'),
                'acto_fallo': info.get('fecha_fallo')
            },
            'contacto': {
                'emails': [info.get('correo_electronico')] if info.get('correo_electronico') else [],
                'responsable': info.get('responsable_captura')
            }
        }
    }
    
    return detalle

def procesar_textos_comprasmx():
    """Procesar los textos copiados y crear archivos JSON"""
    
    # Los dos textos que copiaste
    textos = [
        # Primer texto - Licitación SICT
        """LICITACIÓN PÚBLICA
Código del expediente:
E-2025-00077176
Número de procedimiento de contratación:
LA-09-632-009000985-N-19-2025
Estatus del procedimiento de contratación:
VIGENTE
Compra consolidada:
NO
DATOS GENERALES

DATOS DEL ENTE CONTRATANTE
Dependencia o Entidad:
009000 - INFRAESTRUCTURA, COMUNICACIONES Y TRANSPORTES
Ramo:
09 - INFRAESTRUCTURA, COMUNICACIONES Y TRANSPORTES
Unidad compradora:
009000985 CENTRO SICT GUERRERO
Responsable de la captura:
JAQUELINE ALVARADO AGUERO
Correo electrónico unidad compradora:
jalvague@sct.gob.mx
Unidades Requirentes
009000985 - CENTRO SCT GUERRERO
DATOS GENERALES
Número de procedimiento de contratación:
LA-09-632-009000985-N-19-2025
Referencia / Número de control interno:
SICT-632-NAL-005-2025
Nombre del procedimiento de contratación:
ADQUISICIÓN DE ACCESORIOS Y HERRAMIENTAS MENORES (LLANTAS)
Descripción detallada del procedimiento de contratación:
ADQUISICIÓN DE ACCESORIOS Y HERRAMIENTAS MENORES (LLANTAS)
Ley/Soporte normativo que rige la contratación:
LEY DE ADQUISICIONES, ARRENDAMIENTOS Y SERVICIOS DEL SECTOR PÚBLICO
Tipo de procedimiento de contratación:
LICITACIÓN PÚBLICA
Entidad Federativa donde se llevará a cabo la contratación:
GUERRERO
Año del ejercicio presupuestal:
2025
Procedimiento exclusivo para MIPYMES:
NO""",

        # Segundo texto - Licitación SSBCS
        """LICITACIÓN PÚBLICA
Código del expediente:
E-2025-00072468
Número de procedimiento de contratación:
LA-62-O27-903006996-N-9-2025
Estatus del procedimiento de contratación:
VIGENTE
Compra consolidada:
NO
DATOS GENERALES

DATOS DEL ENTE CONTRATANTE
Dependencia o Entidad:
062O27 - SECRETARÍA DE SALUD
Ramo:
62 - BAJA CALIFORNIA SUR
Unidad compradora:
903006996 DIRECCIÓN DE ADMINISTRACIÓN Y FINANZAS
Responsable de la captura:
NORA KARIME NORIEGA SOLTERO
Correo electrónico unidad compradora:
nora.noriega@saludbcs.gob.mx
Unidades Requirentes
903006996 - DIRECCIÓN DE ADMINISTRACIÓN Y FINANZAS
DATOS GENERALES
Número de procedimiento de contratación:
LA-62-O27-903006996-N-9-2025
Referencia / Número de control interno:
LA-62-O27-903006996-N-9-2025
Nombre del procedimiento de contratación:
SERVICIO DE APOYO ADMINISTRATIVO, TRADUCCIÓN, FOTOCOPIADO E IMPRESIÓN
Descripción detallada del procedimiento de contratación:
SERVICIO DE APOYO ADMINISTRATIVO, TRADUCCIÓN, FOTOCOPIADO E IMPRESIÓN
Ley/Soporte normativo que rige la contratación:
LEY DE ADQUISICIONES, ARRENDAMIENTOS Y SERVICIOS DEL SECTOR PÚBLICO
Tipo de procedimiento de contratación:
LICITACIÓN PÚBLICA
Entidad Federativa donde se llevará a cabo la contratación:
BAJA CALIFORNIA SUR
Año del ejercicio presupuestal:
2025
Procedimiento exclusivo para MIPYMES:
NO"""
    ]
    
    # Crear directorio de detalles
    detalles_dir = Path("data/raw/comprasmx/detalles")
    detalles_dir.mkdir(parents=True, exist_ok=True)
    
    detalles_creados = []
    
    for i, texto in enumerate(textos, 1):
        print(f"\nProcesando texto {i}...")
        
        # Extraer información
        info = extraer_informacion_comprasmx(texto)
        
        if info.get('codigo_expediente'):
            # Crear JSON
            detalle = crear_detalle_json(info)
            
            # Guardar archivo
            codigo = info['codigo_expediente']
            filename = f"detalle_{codigo}.json"
            filepath = detalles_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(detalle, f, ensure_ascii=False, indent=2)
            
            detalles_creados.append(codigo)
            print(f"✅ Creado: {filename}")
            print(f"   Código: {codigo}")
            print(f"   Número: {info.get('numero_procedimiento')}")
            print(f"   Nombre: {info.get('nombre_procedimiento')}")
        else:
            print(f"❌ No se pudo extraer código del expediente del texto {i}")
    
    # Crear índice
    if detalles_creados:
        indice = {
            'fecha_creacion': datetime.now().isoformat(),
            'total_detalles': len(detalles_creados),
            'detalles': {
                codigo: {
                    'archivo': f"detalle_{codigo}.json",
                    'metodo_creacion': 'conversion_manual'
                }
                for codigo in detalles_creados
            }
        }
        
        indice_path = detalles_dir / "indice_detalles.json"
        with open(indice_path, 'w', encoding='utf-8') as f:
            json.dump(indice, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Índice creado con {len(detalles_creados)} detalles")
    
    print(f"\n📊 RESUMEN:")
    print(f"   Detalles creados: {len(detalles_creados)}")
    print(f"   Carpeta: {detalles_dir}")
    print(f"\nArchivos creados:")
    for codigo in detalles_creados:
        print(f"   - detalle_{codigo}.json")
    print(f"   - indice_detalles.json")
    
    return len(detalles_creados)

if __name__ == "__main__":
    print("CONVERSOR DE TEXTO COMPRASMX A JSON")
    print("="*50)
    print("Procesando textos copiados...")
    
    total = procesar_textos_comprasmx()
    
    if total > 0:
        print(f"\n🎉 ÉXITO: {total} archivos JSON creados")
        print("\nAhora ejecuta:")
        print("python test_end_to_end.py")
        print("\nPara verificar que el extractor integra los detalles correctamente")
    else:
        print("\n❌ No se pudieron crear archivos JSON")
