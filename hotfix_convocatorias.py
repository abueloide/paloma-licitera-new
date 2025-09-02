    def encontrar_paginas_convocatorias(self, txt_path: str) -> Tuple[int, int]:
        """
        Encuentra las páginas que contienen convocatorias leyendo el ÍNDICE del DOF
        USANDO LA LÓGICA EXACTA que ya funciona
        
        Returns:
            (inicio, fin) - números de página donde están las convocatorias
        """
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except Exception as e:
            print(f"[ERROR] No se pudo leer {txt_path}: {e}")
            return 1, 100  # fallback
        
        # Buscar marcadores de página y crear diccionario de páginas
        patron_pagina = re.compile(r'=====\s*\[PÁGINA\s+(\d+)\]\s*=====', re.IGNORECASE)
        marcadores = list(patron_pagina.finditer(contenido))
        
        if not marcadores:
            print("[WARN] No se encontraron marcadores de página")
            return 1, 100
        
        # Crear diccionario de páginas como en tu código
        paginas = {}
        for i, marcador in enumerate(marcadores):
            numero_pagina = int(marcador.group(1))
            inicio_pagina = marcador.start()
            
            if i + 1 < len(marcadores):
                fin_pagina = marcadores[i + 1].start()
            else:
                fin_pagina = len(contenido)
            
            paginas[numero_pagina] = contenido[inicio_pagina:fin_pagina]
        
        print("[INFO] Buscando páginas de convocatorias en el índice del DOF...")
        
        # USAR TU LÓGICA EXACTA
        patron_indice_convocatorias = re.compile(
            r'CONVOCATORIAS?\s+PARA\s+CONCURSOS?.*?(\d+)', 
            re.IGNORECASE | re.DOTALL
        )
        patron_indice_avisos = re.compile(
            r'AVISOS?.*?(\d+)', 
            re.IGNORECASE | re.DOTALL
        )
        
        # Buscar en las primeras páginas (típicamente el índice está en páginas 2-4)
        for num_pag in range(1, min(10, max(paginas.keys()) + 1)):
            if num_pag not in paginas:
                continue
                
            contenido_pagina = paginas[num_pag]
            
            # Buscar "CONVOCATORIAS PARA CONCURSOS..."
            match_conv = patron_indice_convocatorias.search(contenido_pagina)
            if match_conv:
                pagina_inicio = int(match_conv.group(1))
                print(f"[INFO] Encontrado inicio de convocatorias en página {pagina_inicio}")
                
                # Buscar "AVISOS" para determinar el fin
                match_avisos = patron_indice_avisos.search(contenido_pagina)
                if match_avisos:
                    pagina_fin = int(match_avisos.group(1)) - 1
                    print(f"[INFO] Encontrado fin de convocatorias en página {pagina_fin}")
                    return pagina_inicio, pagina_fin
                else:
                    # Si no hay avisos, buscar la última página
                    pagina_fin = max(paginas.keys())
                    print(f"[INFO] No se encontraron avisos, usando última página {pagina_fin}")
                    return pagina_inicio, pagina_fin
        
        print("[WARN] No se encontró el rango de convocatorias en el índice")
        
        # Fallback: buscar directamente en el contenido
        print("[INFO] Buscando convocatorias directamente en el contenido...")
        for num_pag, contenido_pag in paginas.items():
            if re.search(r'CONVOCATORIAS?\s+PARA\s+CONCURSOS?', contenido_pag, re.IGNORECASE):
                inicio_conv = num_pag
                print(f"[INFO] Convocatorias encontradas directamente en página {inicio_conv}")
                
                # Buscar avisos después de esta página
                for num_pag2 in range(inicio_conv + 1, max(paginas.keys()) + 1):
                    if num_pag2 in paginas:
                        if re.search(r'AVISOS?', paginas[num_pag2], re.IGNORECASE):
                            fin_conv = num_pag2 - 1
                            print(f"[INFO] Avisos encontrados en página {num_pag2}, convocatorias hasta {fin_conv}")
                            return inicio_conv, fin_conv
                
                # Si no hay avisos, usar hasta el final
                fin_conv = max(paginas.keys())
                print(f"[INFO] No hay avisos, convocatorias hasta página {fin_conv}")
                return inicio_conv, fin_conv
        
        # Último fallback
        print("[WARN] No se pudo determinar rango, procesando todo el documento")
        return 1, max(paginas.keys())