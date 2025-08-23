#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Procesador de archivos ZIP de PAAAPS (Tianguis Digital)
"""

import zipfile
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ZipProcessor:
    """Procesador para archivos ZIP de PAAAPS del Tianguis Digital."""
    
    def procesar(self, zip_path: Path) -> List[Dict[str, Any]]:
        """
        Procesar archivo ZIP de PAAAPS.
        
        Args:
            zip_path: Ruta al archivo ZIP
            
        Returns:
            Lista de licitaciones procesadas
        """
        logger.info(f"Procesando ZIP: {zip_path.name}")
        
        # 1. Extraer archivo JSON del ZIP
        extract_dir = zip_path.parent / f"{zip_path.stem}_extracted"
        extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Buscar archivo JSON
        json_files = list(extract_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No se encontró archivo JSON en {zip_path}")
        
        json_path = json_files[0]
        
        # 2. Leer y limpiar JSON
        with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()
        
        # Quitar cabeceras HTTP si existen
        clean_text = re.split(r"\n\n", raw_text, maxsplit=1)[-1].strip()
        
        # 3. Parsear JSON (puede tener doble encoding)
        try:
            # Primera capa
            parsed_outer = json.loads(clean_text)
        except json.JSONDecodeError:
            # Intentar quitar comillas extras
            parsed_outer = json.loads(clean_text.strip('"'))
        
        # Segunda capa (si es necesario)
        if isinstance(parsed_outer, str):
            data = json.loads(parsed_outer)
        else:
            data = parsed_outer
        
        # 4. Convertir a formato estándar
        licitaciones = []
        
        for rec in data:
            licitacion = self._parsear_registro_ocds(rec)
            if licitacion:
                licitaciones.append(licitacion)
        
        # 5. Limpiar archivos temporales
        for file in extract_dir.glob("*"):
            file.unlink()
        extract_dir.rmdir()
        
        logger.info(f"Extraídas {len(licitaciones)} licitaciones del ZIP")
        return licitaciones
    
    def _parsear_registro_ocds(self, rec: Dict) -> Dict[str, Any]:
        """
        Parsear un registro OCDS a formato estándar.
        
        Args:
            rec: Registro en formato OCDS
            
        Returns:
            Licitación en formato estándar
        """
        try:
            # Extraer campos básicos
            ocid = rec.get("ocid", "")
            buyer = rec.get("buyer", {})
            planning = rec.get("planning", {})
            tender = rec.get("tender", {})
            
            # Extraer información de planning/budget
            budget = planning.get("budget", {})
            budget_amount = budget.get("amount", {})
            
            # Extraer información de tender
            tender_value = tender.get("value", {})
            
            # Determinar tipo de procedimiento
            procurement_method = tender.get("procurementMethod", "")
            if procurement_method == "open":
                tipo_procedimiento = "LICITACION_PUBLICA"
            elif procurement_method == "selective":
                tipo_procedimiento = "INVITACION_3"
            else:
                tipo_procedimiento = "ADJUDICACION_DIRECTA"
            
            # Construir licitación
            licitacion = {
                'numero_procedimiento': ocid or rec.get("id", ""),
                'titulo': tender.get("title") or budget.get("project", ""),
                'descripcion': tender.get("description"),
                'entidad_compradora': self._extraer_nombre(buyer),
                'unidad_compradora': None,
                'tipo_procedimiento': tipo_procedimiento,
                'tipo_contratacion': self._mapear_categoria(tender.get("mainProcurementCategory")),
                'estado': self._mapear_estado(tender.get("status")),
                'fecha_publicacion': self._parsear_fecha(rec.get("date")),
                'fecha_apertura': self._parsear_fecha(tender.get("tenderPeriod", {}).get("startDate")),
                'fecha_fallo': None,
                'monto_estimado': self._extraer_monto(budget_amount) or self._extraer_monto(tender_value),
                'moneda': budget_amount.get("currency") or tender_value.get("currency", "MXN"),
                'proveedor_ganador': None,
                'fuente': 'TIANGUIS_ZIP',
                'url_original': f"https://tianguisdigital.cdmx.gob.mx/ocds/tender/{ocid}" if ocid else None,
                'datos_originales': rec
            }
            
            return licitacion
            
        except Exception as e:
            logger.error(f"Error parseando registro OCDS: {e}")
            return None
    
    def _extraer_nombre(self, buyer: Any) -> str:
        """Extraer nombre del comprador."""
        if isinstance(buyer, str):
            return buyer
        elif isinstance(buyer, dict):
            return buyer.get("name", "")
        return ""
    
    def _extraer_monto(self, amount: Any) -> float:
        """Extraer monto numérico."""
        if isinstance(amount, (int, float)):
            return float(amount)
        elif isinstance(amount, dict):
            return float(amount.get("amount", 0) or 0)
        return None
    
    def _parsear_fecha(self, fecha_str: str) -> datetime:
        """Parsear fecha ISO."""
        if not fecha_str:
            return None
        try:
            # Remover timezone si existe
            fecha_str = fecha_str.split('T')[0]
            return datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except:
            return None
    
    def _mapear_categoria(self, categoria: str) -> str:
        """Mapear categoría OCDS a tipo de contratación."""
        if not categoria:
            return "ADQUISICIONES"
        
        categoria_lower = categoria.lower()
        if categoria_lower == "goods":
            return "ADQUISICIONES"
        elif categoria_lower == "works":
            return "OBRA_PUBLICA"
        elif categoria_lower == "services":
            return "SERVICIOS"
        else:
            return "ADQUISICIONES"
    
    def _mapear_estado(self, estado: str) -> str:
        """Mapear estado OCDS a estado estándar."""
        if not estado:
            return "VIGENTE"
        
        estado_lower = estado.lower()
        if estado_lower in ["active", "planning"]:
            return "VIGENTE"
        elif estado_lower in ["complete", "terminated"]:
            return "CERRADO"
        elif estado_lower == "cancelled":
            return "CANCELADO"
        else:
            return "VIGENTE"
