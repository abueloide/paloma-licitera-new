#!/usr/bin/env python3
"""
Test del Scraper Optimizado - Versión de Prueba
Prueba con solo 5 registros para verificar funcionalidad
"""

import os
from comprasmx_scraper_optimizado import ComprasMXScraperOptimizado

def test_scraper():
    """Función de prueba con configuración limitada"""
    print("🧪 INICIANDO PRUEBA DEL SCRAPER OPTIMIZADO")
    print("=" * 50)
    
    # Configuración de prueba
    LIMITE_PRUEBA = 5
    HEADLESS = False  # Para ver qué pasa
    
    # Verificar clave de Anthropic (opcional para la prueba)
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        print("✅ Clave de Anthropic detectada - usará IA")
    else:
        print("⚠️  Sin clave de Anthropic - usará regex")
    
    # Ejecutar scraper
    scraper = ComprasMXScraperOptimizado(anthropic_api_key=api_key)
    
    try:
        resultados = scraper.ejecutar_scraping_completo(
            limite=LIMITE_PRUEBA, 
            headless=HEADLESS
        )
        
        print(f"\n📊 RESULTADOS DE LA PRUEBA:")
        print(f"  📋 Total procesadas: {resultados['total_procesadas']}")
        print(f"  🔑 UUIDs exitosos: {resultados['uuids_exitosos']}")
        print(f"  📊 Datos completos: {resultados['datos_completos']}")
        print(f"  ❌ Errores: {resultados['errores']}")
        
        # Calcular tasa de éxito
        if resultados['total_procesadas'] > 0:
            tasa_exito = (resultados['uuids_exitosos'] / resultados['total_procesadas']) * 100
            print(f"  📈 Tasa de éxito: {tasa_exito:.1f}%")
            
            if tasa_exito >= 80:
                print("🎉 ¡PRUEBA EXITOSA! El scraper está funcionando bien")
                return True
            elif tasa_exito >= 50:
                print("⚠️  Prueba parcial - necesita mejoras")
                return False
            else:
                print("❌ Prueba fallida - requiere revisión")
                return False
        else:
            print("❌ No se procesaron registros")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {str(e)}")
        return False

if __name__ == "__main__":
    exito = test_scraper()
    if exito:
        print("\n✅ ¡Listo para ejecutar con más registros!")
    else:
        print("\n🔧 Necesita ajustes antes de ejecutar en grande")