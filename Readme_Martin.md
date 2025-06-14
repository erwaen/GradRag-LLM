# Guía de Uso - GradRag-LLM

Los pasos necesarios a seguir para poder probar todas las implementaciones para el proyecto.

## Prerrequisitos

- Docker y Docker Compose instalados
- Archivo `.env` configurado con las variables de entorno necesarias
- Conexión a internet para el scraping

## Paso 1: Levantar el Proyecto

### 1.1 Construcción y ejecución inicial
```bash
# Desde el directorio GradRag-LLM/
sudo docker-compose up --build
```

### 1.2 Verificar que el servicio esté corriendo
Una vez que veas en la consola que FastAPI está corriendo, el backend estará disponible en:
- **API Backend**: http://127.0.0.1:8000
- **Documentación Swagger**: http://127.0.0.1:8000/docs

## Paso 2: Scraping de Profesores

### 2.1 Acceder a la documentación de la API
1. Ve a **http://127.0.0.1:8000/docs**
2. Busca la sección **"Professor Router"**

### 2.2 Verificar estado del router
Antes de comenzar el scraping, verifica que el sistema esté listo:

**Endpoint**: `GET /api/professor/status`
- Haz clic en el endpoint
- Presiona **"Try it out"**
- Ejecuta la petición

### 2.3 Ejecutar el scraping
**Endpoint**: `POST /api/professor/scrape`

1. Haz clic en el endpoint de scraping
2. Presiona **"Try it out"**
3. Modifica el cuerpo de la petición según tus necesidades:

```json
{
  "max_professors": 10,
  "save_file": "/app/logs/scraped_professors.json",
  "max_workers": 10,
  "use_cache": true
}
```

#### Parámetros explicados:
- **max_professors**: Cantidad máxima de profesores a scrapear (ej: 10, 50, 100)
- **save_file**: Ruta y nombre del archivo JSON donde se guardarán los datos
- **max_workers**: Número de hilos paralelos para acelerar el scraping
- **use_cache**: Si usar caché para evitar re-scrapear páginas ya procesadas

4. Presiona **"Execute"** para iniciar el scraping

**Nota**: El scraping puede tomar varios minutos dependiendo de la cantidad de profesores.

## Paso 3: Procesar los Datos Scrapeados

Una vez completado el scraping, necesitas procesar los datos para prepararlos para Qdrant:

### 3.1 Ejecutar el script de procesamiento
```bash
# Abrir una terminal en el contenedor
sudo docker-compose exec gradrag-app bash

# Verificar que data/raw exista con:
ls data/raw >/dev/null 2>&1 && echo "Exists" || echo "Does not exist"

# Si no existe crear el path
mkdir -p data/raw

# Ejecutar el script de procesamiento
python crawler/parse_scraped_data.py
```

Este script:
- Lee el archivo JSON generado por el scraper
- Transforma los datos al formato requerido por Qdrant
- Prepara los documentos para la indexación vectorial

## Paso 4: Almacenar en la Base de Datos Vectorial

### 4.1 Usar el endpoint de almacenamiento
Regresa a **http://127.0.0.1:8000/docs** y busca:

**Endpoint**: `GET /api/professor/doc_advisor`

1. Haz clic en el endpoint
2. Presiona **"Try it out"**
3. Ejecuta la petición

Este endpoint:
- Obtiene los documentos procesados
- Los almacena en Qdrant con embeddings vectoriales
- Prepara los datos para consultas RAG

### 4.2 Verificar almacenamiento exitoso
La respuesta debería ser:
```json
{
  "message": "Documents stored"
}
```

## Comandos Útiles

### Acceder al contenedor para debugging:
```bash
sudo docker-compose exec gradrag-app bash
```

### Reiniciar el servicio:
```bash
sudo docker-compose restart gradrag-app
```

## Estructura de Archivos Generados

Después del proceso completo tendrás:
```
/app/logs/
├── scraped_professors.json     # Datos raw del scraping
```

## Conclusión

Una vez completados todos los pasos, tu sistema GradRag-LLM estará listo para:
- Realizar consultas RAG sobre información de profesores
- Responder preguntas sobre asesores académicos
- Proporcionar recomendaciones basadas en los datos scrapeados