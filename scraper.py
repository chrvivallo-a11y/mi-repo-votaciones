import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os

# ==========================================
# FUNCIONES DE EXTRACCIÓN
# ==========================================

def obtener_ultimo_id_disponible(scraper):
    """
    Visita la página principal de votaciones y busca el ID más alto disponible.
    """
    url_indice = "https://www.camara.cl/legislacion/sala_sesiones/votaciones.aspx"
    try:
        response = scraper.get(url_indice, timeout=15)
        if response.status_code == 200:
            # Buscamos en todo el código fuente cualquier número asociado a prmIdVotacion
            ids_encontrados = re.findall(r'prmIdVotacion=(\d+)', response.text)
            if ids_encontrados:
                ids_enteros = [int(id_voto) for id_voto in ids_encontrados]
                return max(ids_enteros)
    except Exception as e:
        print(f"Error al buscar el último ID en el índice: {e}")
    return None

def obtener_datos_votacion(scraper, id_votacion):
    """
    Extrae los datos de una votación específica.
    """
    url = f"https://www.camara.cl/legislacion/sala_sesiones/votacion_detalle.aspx?prmIdVotacion={id_votacion}"
    
    try:
        response = scraper.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"  [!] ID {id_votacion}: Error HTTP {response.status_code}.")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Validamos que la página contenga la estructura de ficha[cite: 1]
        if not soup.find('div', class_='datos-ficha'):
            print(f"  [!] ID {id_votacion}: Cargó, pero no tiene la estructura de votación.")
            return None
            
        datos_sesion = {
            "ID Votacion": id_votacion,
            "Proyecto De Ley": "", "Fecha": "", "Materia": "",
            "Artículo": "", "Trámite": "", "Tipo de Votación": "",
            "Quorum": "", "Resultado": ""
        }
        
        # Extraemos la metadata de la votación[cite: 1]
        fichas = soup.find_all('div', class_='datos-ficha')
        for div in fichas:
            dato = div.find('div', class_='dato')
            info = div.find('div', class_='info')
            
            if dato and info:
                llave_texto = dato.text.replace(':', '').strip().lower()
                valor = info.text.strip()
                
                if 'proyecto' in llave_texto: datos_sesion["Proyecto De Ley"] = valor
                elif 'fecha' in llave_texto: datos_sesion["Fecha"] = valor
                elif 'materia' in llave_texto: datos_sesion["Materia"] = valor
                elif 'artículo' in llave_texto or 'articulo' in llave_texto: datos_sesion["Artículo"] = valor
                elif 'trámite' in llave_texto or 'tramite' in llave_texto: datos_sesion["Trámite"] = valor
                elif 'tipo de votación' in llave_texto or 'tipo de votacion' in llave_texto: datos_sesion["Tipo de Votación"] = valor
                elif 'quorum' in llave_texto: datos_sesion["Quorum"] = valor
                elif 'resultado' in llave_texto: datos_sesion["Resultado"] = valor

        def extraer_nombres(titulo_seccion):
            header = soup.find('h3', class_='colTitle', string=re.compile(titulo_seccion, re.IGNORECASE))
            if not header:
                return []
            contenedor = header.find_next_sibling('div')
            if not contenedor:
                return []
            return [a.text.strip() for a in contenedor.find_all('a')]

        a_favor = extraer_nombres('A Favor')
        en_contra = extraer_nombres('En Contra')
        abstenciones = extraer_nombres('Abstención')
        pareos = extraer_nombres('Pareos')

        filas_votantes = []

        def agregar_filas(lista_nombres, tipo_voto):
            for votante in lista_nombres:
                fila = datos_sesion.copy()
                fila['Votante'] = votante
                fila['Voto_Emitido'] = tipo_voto
                filas_votantes.append(fila)

        agregar_filas(a_favor, 'A Favor')
        agregar_filas(en_contra, 'En Contra')
        agregar_filas(abstenciones, 'Abstención')
        agregar_filas(pareos, 'Pareo')

        print(f"  [✓] ID {id_votacion}: Extraídos {len(filas_votantes)} votos individuales.")
        return filas_votantes

    except Exception as e:
        print(f"  [X] ID {id_votacion}: Excepción generada -> {e}")
        return None

# ==========================================
# BLOQUE PRINCIPAL (MOTOR DE ACTUALIZACIÓN)
# ==========================================
if __name__ == "__main__":
    archivo_txt = "resultados_votaciones.txt"
    
    # 1. Leer IDs ya almacenados para no repetir trabajo
    ids_existentes = set()
    if os.path.exists(archivo_txt) and os.path.getsize(archivo_txt) > 0:
        try:
            df_historial = pd.read_csv(archivo_txt, sep='\t')
            if 'ID Votacion' in df_historial.columns:
                ids_existentes = set(df_historial['ID Votacion'].dropna().astype(int))
            print(f"Historial cargado. Se encontraron {len(ids_existentes)} votaciones previas.")
        except Exception as e:
            print(f"Aviso: No se pudo leer el historial correctamente. {e}")

    # 2. Inicializar el Scraper (Evadiendo Cloudflare)
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    # 3. Detectar el último ID publicado en la web
    print("Buscando el último ID disponible en la Cámara...")
    ultimo_id = obtener_ultimo_id_disponible(scraper)
    
    if not ultimo_id:
        print("No se pudo detectar el último ID. Abortando ejecución.")
        exit()
        
    print(f"Último ID detectado: {ultimo_id}")
    
    # 4. Calcular el rango de los últimos 100 IDs
    id_inicio = max(1, ultimo_id - 100) # Evitamos números negativos
    
    # Filtramos para quedarnos SOLO con los IDs que NO están en nuestro historial
    ids_a_extraer = [vid for vid in range(id_inicio, ultimo_id + 1) if vid not in ids_existentes]
    
    if not ids_a_extraer:
        print("La base de datos está actualizada. No hay votaciones nuevas que extraer.")
    else:
        print(f"Se extraerán {len(ids_a_extraer)} votaciones nuevas...")
        
        resultados_nuevos = []
        
        for current_id in sorted(ids_a_extraer):
            filas_extraidas = obtener_datos_votacion(scraper, current_id)
            
            if filas_extraidas:
                resultados_nuevos.extend(filas_extraidas)
                
            time.sleep(2) # Pausa ética para evitar bloqueos
            
        # 5. Guardar los resultados en modo Append (Añadir al final)
        if len(resultados_nuevos) > 0:
            df_nuevos = pd.DataFrame(resultados_nuevos)
            
            # Verificamos si el archivo es nuevo para saber si le ponemos las cabeceras (headers)
            es_nuevo = not os.path.exists(archivo_txt) or os.path.getsize(archivo_txt) == 0
            
            # mode='a' significa Append. Agregará las filas abajo sin borrar lo viejo.
            df_nuevos.to_csv(archivo_txt, mode='a', sep='\t', index=False, header=es_nuevo, encoding='utf-8-sig')
            
            print(f"\n¡Actualización exitosa! Se añadieron {len(resultados_nuevos)} filas nuevas al archivo '{archivo_txt}'.")
        else:
            print("\nSe recorrieron los IDs, pero no se extrajeron datos válidos (posiblemente sesiones suspendidas o IDs vacíos).")