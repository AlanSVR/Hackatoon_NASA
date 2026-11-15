# Especificación funcional y no funcional

## Fuente y criterio de interpretación

Los requisitos de esta especificación se contrastaron con el PDF entregado el 14 de noviembre de 2026. El prototipo HTML recibido es una referencia de organización de controles y estados visuales, no una especificación científica ni una fuente de datos.

Cuando ambos materiales difieren, prevalece esta regla: la aplicación nunca mostrará una clasificación, porcentaje de cobertura, animación temporal o capa científica si no existe un producto real, trazable y validado que la respalde.

## Requisitos funcionales incorporados

| Requisito del documento | Resolución en el MVP |
| --- | --- |
| Delimitar zona por ratón y ubicar lugares específicos. | Selector de país/localidad y herramientas de punto, rectángulo y polígono; se puede limpiar la selección. |
| Clasificación supervisada, filtros, porcentajes, colores y leyenda. | Pendiente de un raster espacial, entrenamiento y validación. El MVP no inventa clases, colores ni porcentajes. |
| Comparar antes/después por año, de 2020 a 2025, con animación. | Comparador numérico anual de una serie puntual. La comparación y animación espaciales quedan bloqueadas hasta contar con datos raster validados y un catálogo de fechas reales. |
| Pantalla informativa de equipo/autores y reinicio. | Modal «Acerca de» y acción «Restablecer filtros». |
| Bases de mapa oscuras, simples y con alternativas. | Cinco mapas base sin clave: oscuro, claro, satélite, topográfico y OpenStreetMap. |
| Datos relevantes y filtros claros. | Variables, unidad, fuente, período, calidad y limitaciones visibles antes y después de la consulta. |

El requerimiento gráfico de una marca NASA se interpreta como contexto del reto, no como autorización para usar la insignia oficial. AndesSAR conserva una marca propia y declara que no está afiliado a NASA.

## Funcional actual

- Seleccionar Ecuador, Estados Unidos o Canadá y una localidad configurada.
- Mostrar un mapa Leaflet con controles de zoom, punto/rectángulo/polígono y limpieza de selección.
- Elegir una base cartográfica sin usar ni exponer una API key. El inicio es estático en la localidad configurada; no se solicita geolocalización del navegador.
- Solicitar series mensuales puntuales de NASA POWER mediante FastAPI para variables declaradas.
- Mostrar serie original, anomalías con período base explícito, agregados anuales, tendencia lineal, IC 95 %, p y advertencias.
- Comparar dos años sin denominar la diferencia una tendencia estadísticamente significativa.
- Conservar selección y filtros durante el cambio de paneles, permitir restablecerlos y exportar los resultados realmente devueltos por la API.
- Conservar la comparación SAR como módulo experimental y claramente separado.

## Sistema de referencia de coordenadas

- El mapa de Leaflet y sus cinco bases se visualizan en Web Mercator, `EPSG:3857`.
- Las coordenadas que el usuario selecciona y las solicitudes a NASA POWER se manejan como latitud/longitud WGS 84, `EPSG:4326`. Se muestran en el mapa para comprobación.
- El módulo SAR de Riobamba reproyecta para calcular área en `EPSG:32717` (UTM 17S). Esa proyección no se reutiliza para Ecuador entero, Estados Unidos ni Canadá.
- Un futuro raster debe registrar CRS de origen, CRS de análisis, resolución, extensión, nodata, método de remuestreo y versión. El análisis de áreas debe usar una proyección métrica o equivalente adecuada para el AOI, y toda transformación debe ejecutarse explícitamente con Rasterio/PROJ.

## No funcional

- La API local escucha en `127.0.0.1`; no se exponen credenciales ni se aceptan URLs arbitrarias de proveedores.
- Consultas externas con timeout, errores comprensibles y caché TTL local.
- Validación Pydantic de fechas, coordenadas, país, región y combinaciones de comparación.
- Datos faltantes, procedencia, unidades y limitaciones quedan visibles en las respuestas.
- Diseño responsive, semántico y con contraste suficiente; ningún color es el único indicador de estado.
- El análisis no fabrica capas, clasificaciones, promedios espaciales ni causalidad.
