# scanner/agent/multi_account_agent.py
from pydantic_ai import Agent, BinaryContent
from dotenv import load_dotenv
from .output import ReporteAnalisisSuelo
import os
from typing import List
import time
import logging
import PyPDF2
import io

load_dotenv()

class MultiAccountAgent:
    def __init__(self):
        # Configurar múltiples API keys
        self.api_keys = [
            os.getenv("GEMINI_API_KEY"),      # Tu API key original
            os.getenv("GEMINI_API_KEY_1"),    # Si es diferente a la original
            os.getenv("GEMINI_API_KEY_2"), 
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4")     # Añade más si tienes
        ]
        
        # Filtrar keys válidas
        self.api_keys = [key for key in self.api_keys if key]
        
        if not self.api_keys:
            raise ValueError("No se encontraron API keys válidas. Configura GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc. en tu .env")
        
        self.current_key_index = 0
        self.retry_delays = [5, 10, 20, 30, 60]  # Delays progresivos
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Crear agente inicial
        self.agent = self._create_agent()
        
        self.logger.info(f"MultiAccountAgent inicializado con {len(self.api_keys)} API keys")
        
    def _create_agent(self):
        """Crea un nuevo agente con la API key actual"""
        current_key = self.api_keys[self.current_key_index]
        
        # Configurar la variable de entorno para el agente
        os.environ["GOOGLE_API_KEY"] = current_key
        
        return Agent(
            "gemini-2.5-flash",
            system_prompt=(
                """Eres un extractor de datos de documentos especializado en análisis de suelo. 
                
                INSTRUCCIONES IMPORTANTES:
                1. Extrae TODOS los reportes de análisis de suelo que encuentres en el documento
                2. Cada hoja/página del PDF puede contener uno o más reportes
                3. Procesa cada reporte por separado y completo
                4. Si una página no contiene datos de análisis de suelo, omítela
                5. Extrae TODA la información disponible para cada reporte siguiendo estrictamente la estructura ReporteAnalisisSuelo
                6. Si un campo no tiene información, déjalo como cadena vacía ""
                7. No inventes datos - solo extrae lo que está claramente visible
                8. Sé muy meticuloso con los valores numéricos y sus unidades
                
                FORMATO DE SALIDA:
                - Devuelve una lista de objetos ReporteAnalisisSuelo
                - Un objeto por cada reporte encontrado
                - Incluye TODOS los campos disponibles del modelo
                
                CAMPOS CRÍTICOS A EXTRAER:
                - Información del solicitante (nombre, dirección, teléfono, etc.)
                - Datos de la muestra (fecha, ubicación, cultivo, etc.)  
                - Parámetros físicos del suelo (textura, densidad, etc.)
                - Parámetros químicos (pH, conductividad, materia orgánica, etc.)
                - Nutrientes y micronutrientes con sus interpretaciones
                - Relaciones entre cationes
                
                Si el documento tiene muchas páginas, procesa cada una cuidadosamente."""
            ),
            output_type=List[ReporteAnalisisSuelo]
        )
    
    def _rotate_api_key(self):
        """Rota a la siguiente API key disponible"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.logger.info(f"Rotando a API key #{self.current_key_index + 1}/{len(self.api_keys)}")
        self.agent = self._create_agent()
    
    def _is_quota_exceeded_error(self, error):
        """Detecta si el error es por límite de cuota/tokens o sobrecarga del modelo"""
        error_str = str(error).lower()
        quota_indicators = [
            "quota exceeded",
            "rate limit",
            "too many requests", 
            "content field missing",  # Este es el error que estás viendo
            "resource exhausted",
            "usage_metadata",
            "token limit",
            "429",  # HTTP status code for rate limiting
            "503",  # HTTP status code for service unavailable
            "overloaded",  # Model overloaded
            "unavailable",  # Service unavailable
            "temporarily unavailable",
            "server overloaded",
            "internal error",
            "service temporarily unavailable"
        ]
        return any(indicator in error_str for indicator in quota_indicators)
    
    def _split_pdf_by_pages(self, pdf_content, max_pages_per_chunk=8):  # Reducido a 8 páginas
        """
        Divide el PDF en chunks por páginas usando PyPDF2
        """
        chunks = []
        
        try:
            # Crear un objeto BytesIO desde el contenido
            pdf_stream = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            total_pages = len(pdf_reader.pages)
            
            self.logger.info(f"PDF tiene {total_pages} páginas, dividiendo en chunks de {max_pages_per_chunk} páginas")
            
            for start_page in range(0, total_pages, max_pages_per_chunk):
                end_page = min(start_page + max_pages_per_chunk, total_pages)
                
                # Crear un nuevo PDF con las páginas del chunk
                pdf_writer = PyPDF2.PdfWriter()
                
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Guardar el chunk en bytes
                chunk_stream = io.BytesIO()
                pdf_writer.write(chunk_stream)
                chunk_bytes = chunk_stream.getvalue()
                chunk_stream.close()
                
                chunks.append(chunk_bytes)
                self.logger.info(f"Chunk creado: páginas {start_page + 1}-{end_page} ({len(chunk_bytes)} bytes)")
            
            pdf_stream.close()
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error al dividir PDF: {str(e)}")
            # Si no se puede dividir, devolver el PDF completo
            return [pdf_content]
    
    def run_sync(self, messages, max_retries_per_key=2):  # Reducido el número de reintentos
        """
        Ejecuta el agente con rotación automática de API keys y manejo de chunks
        """
        # Extraer contenido PDF del mensaje
        pdf_content = None
        text_message = None
        
        for message in messages:
            if hasattr(message, 'data') and hasattr(message, 'media_type'):
                if message.media_type == "application/pdf":
                    pdf_content = message.data
            elif isinstance(message, str):
                text_message = message
        
        # Determinar si necesita procesamiento por chunks
        needs_chunking = False
        if pdf_content:
            # Verificar número de páginas
            try:
                pdf_stream = io.BytesIO(pdf_content)
                pdf_reader = PyPDF2.PdfReader(pdf_stream)
                num_pages = len(pdf_reader.pages)
                pdf_stream.close()
                
                # Si tiene más de 12 páginas o el archivo es muy grande, usar chunks
                if num_pages > 12 or len(pdf_content) > 4 * 1024 * 1024:  # 4MB
                    needs_chunking = True
                    self.logger.info(f"PDF con {num_pages} páginas requiere procesamiento por chunks")
                    
            except Exception as e:
                self.logger.warning(f"No se pudo determinar el número de páginas: {e}")
        
        if needs_chunking:
            return self._process_large_pdf(text_message, pdf_content, max_retries_per_key)
        else:
            # Procesamiento normal para PDFs pequeños
            return self._process_normal_pdf(messages, max_retries_per_key)
    
    def _process_normal_pdf(self, messages, max_retries_per_key):
        """Procesa un PDF de tamaño normal sin dividir en chunks"""
        total_attempts = 0
        max_total_attempts = len(self.api_keys) * max_retries_per_key
        
        while total_attempts < max_total_attempts:
            try:
                self.logger.info(f"Intento {total_attempts + 1}/{max_total_attempts} con API key #{self.current_key_index + 1}")
                
                result = self.agent.run_sync(messages)
                self.logger.info("Procesamiento exitoso")
                return result
                
            except Exception as error:
                total_attempts += 1
                error_msg = str(error)
                self.logger.error(f"Error en intento {total_attempts}: {error_msg}")
                
                # Verificar si es error de cuota/sobrecarga
                is_quota_error = self._is_quota_exceeded_error(error)
                self.logger.info(f"¿Es error de cuota/sobrecarga? {is_quota_error}")
                
                if is_quota_error:
                    if total_attempts < max_total_attempts:
                        # Rotar API key y reintentar
                        self.logger.warning(f"Rotando API key debido a: {error_msg}")
                        self._rotate_api_key()
                        
                        # Aplicar delay progresivo
                        delay_index = min(total_attempts - 1, len(self.retry_delays) - 1)
                        delay = self.retry_delays[delay_index]
                        self.logger.info(f"Esperando {delay} segundos antes del siguiente intento...")
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error("Se agotaron todos los intentos con todas las API keys")
                        break
                else:
                    # Error no relacionado con cuota, no reintentar inmediatamente
                    self.logger.error(f"Error no relacionado con cuota: {error_msg}")
                    # Intentar rotar API key de todas formas, por si ayuda
                    if total_attempts < max_total_attempts:
                        self._rotate_api_key()
                        time.sleep(5)
                        continue
                    else:
                        raise error
        
        # Si llegamos aquí, se agotaron todos los intentos
        raise Exception(f"Se agotaron todos los intentos con {len(self.api_keys)} API keys. "
                       f"Total de intentos: {total_attempts}. "
                       f"El documento puede ser demasiado complejo o grande para procesar. "
                       f"Intenta dividir el PDF en secciones más pequeñas.")
    
    def _process_large_pdf(self, text_message, pdf_content, max_retries_per_key):
        """
        Procesa un PDF grande dividiéndolo en chunks por páginas
        """
        # Dividir PDF en chunks por páginas (chunks más pequeños)
        chunks = self._split_pdf_by_pages(pdf_content, max_pages_per_chunk=8)
        self.logger.info(f"PDF dividido en {len(chunks)} chunks")
        
        all_results = []
        
        for i, chunk_pdf_bytes in enumerate(chunks):
            self.logger.info(f"Procesando chunk {i + 1}/{len(chunks)}")
            
            chunk_messages = [
                f"{text_message} (Procesando páginas del chunk {i + 1} de {len(chunks)})",
                BinaryContent(data=chunk_pdf_bytes, media_type="application/pdf")
            ]
            
            # Procesar chunk con rotación de API keys
            total_attempts = 0
            max_total_attempts = len(self.api_keys) * max_retries_per_key
            chunk_processed = False
            
            while total_attempts < max_total_attempts and not chunk_processed:
                try:
                    self.logger.info(f"Procesando chunk {i + 1} - intento {total_attempts + 1} con API key #{self.current_key_index + 1}")
                    
                    result = self.agent.run_sync(chunk_messages)
                    
                    # Extraer resultados del chunk
                    chunk_results = result.output if hasattr(result, 'output') else result
                    if isinstance(chunk_results, list):
                        all_results.extend(chunk_results)
                    else:
                        all_results.append(chunk_results)
                        
                    chunk_processed = True
                    self.logger.info(f"Chunk {i + 1} procesado exitosamente - {len(chunk_results) if isinstance(chunk_results, list) else 1} reportes extraídos")
                    
                except Exception as error:
                    total_attempts += 1
                    self.logger.error(f"Error en chunk {i + 1}, intento {total_attempts}: {str(error)}")
                    
                    if self._is_quota_exceeded_error(error) and total_attempts < max_total_attempts:
                        self._rotate_api_key()
                        delay_index = min(total_attempts - 1, len(self.retry_delays) - 1)
                        delay = self.retry_delays[delay_index]
                        self.logger.info(f"Esperando {delay} segundos antes del siguiente intento...")
                        time.sleep(delay)
                    else:
                        # Si no es error de cuota o se agotaron intentos, fallar
                        if not self._is_quota_exceeded_error(error):
                            self.logger.error(f"Error no relacionado con cuota en chunk {i + 1}: {error}")
                        raise error
            
            if not chunk_processed:
                raise Exception(f"No se pudo procesar el chunk {i + 1} después de {max_total_attempts} intentos")
            
            # Pausa más larga entre chunks para evitar rate limiting
            if i < len(chunks) - 1:  # No pausar después del último chunk
                pause_time = 8  # Pausa de 8 segundos entre chunks
                self.logger.info(f"Pausa de {pause_time} segundos antes del siguiente chunk...")
                time.sleep(pause_time)
        
        self.logger.info(f"Procesamiento completo: {len(all_results)} reportes extraídos en total")
        
        # Crear objeto resultado simulando la estructura esperada
        class Result:
            def __init__(self, output):
                self.output = output
        
        return Result(all_results)

# Crear instancia global
multi_agent = MultiAccountAgent()