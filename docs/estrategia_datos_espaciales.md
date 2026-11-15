# Estrategia de datos espaciales — decisión pendiente de implementación

Este documento responde a la viabilidad de descargar y procesar datos geográficos. No activa nuevas descargas, periodos, clasificaciones ni capas en la aplicación.

## Decisión para el MVP

La aplicación actual debe continuar consultando NASA POWER en línea para sus series puntuales. La respuesta mensual puede consumirse como JSON o CSV, pero no es un raster de cobertura ni una base suficiente para clasificar un área.

Para el futuro módulo espacial, conviene preparar y validar los productos fuera del flujo interactivo de la web; después la aplicación sirve un catálogo local curado de archivos. Así un usuario no técnico solo ve lugares, variables y fechas que sí existen para ese producto, y no puede elegir años incompatibles.

| Caso | Formato aconsejado | Dónde procesar | Viabilidad |
| --- | --- | --- | --- |
| Serie puntual NASA POWER | JSON/CSV desde API; caché temporal | Backend actual | Ya operativo; no requiere descarga masiva. |
| AOI pequeño, conjunto fijo de fechas | Cloud Optimized GeoTIFF (COG) o GeoTIFF, más manifiesto | Rasterio local | Viable si se limita tamaño, AOI y número de bandas. |
| Subconjuntos de productos NASA por región/tiempo | GeoTIFF o NetCDF-4 descargado como trabajo asíncrono | Preparación offline + catálogo local | Viable; requiere autenticación Earthdata y control de trabajos. |
| Mosaicos grandes, clasificación multitemporal o muchos AOI | Exportación reproyectada desde Google Earth Engine, luego COG/GeoTIFF versionado | Earth Engine/Python en fase de preparación | Viable, pero no debe dispararse desde cada clic de un usuario final. |
| Clasificación supervisada | Rasters de entrada + etiquetas de entrenamiento + producto de clase + métricas | Python/GEE, con revisión humana | Solo después de validar muestras, fechas, modelo y exactitud. |

## Por qué no descargar «todo» desde el navegador

- Los GeoTIFF y NetCDF pueden ser pesados; procesarlos en el navegador eleva el tiempo de espera y la memoria, sobre todo en equipos modestos.
- Una descarga de un año no implica que existan todos los años, bandas o calidades. El selector debe derivarse de un manifiesto, no de un campo de texto libre.
- Google Earth Engine puede exportar GeoTIFF/TFRecord, pero una exportación grande es una tarea asíncrona y exige definir región, proyección y transformación de píxel explícitas. Es mejor usarlo para preparar productos reproducibles que como sustituto silencioso de la base de datos de la aplicación.
- La clasificación no se vuelve válida por cambiar el color de un mapa: requiere definición de clases, muestras independientes, fecha/sensor, validación y métricas como matriz de confusión.

## Catálogo mínimo antes de mostrar una capa

Cada producto raster debe tener un registro inmutable, por ejemplo `catalogo_capas.json`, con:

- Identificador de producto, fuente, licencia, sensor y versión de procesamiento.
- AOI y geometría de cobertura en WGS 84 (`EPSG:4326`).
- Fechas exactas disponibles y la regla de composición temporal.
- Ruta a COG/GeoTIFF o NetCDF, checksum, tamaño, bandas, escala, nodata y unidad.
- CRS de origen, CRS de análisis y resolución de píxel.
- Para clases: nombres/códigos, paleta, método, conjunto de entrenamiento, validación, métricas y limitaciones.

La interfaz consultará ese catálogo para poblar los controles. Si no hay capa para una localidad/fecha/variable, la opción se deshabilita con una explicación. No se debe permitir 2012 si el producto solo cubre 2021–2026.

## CRS y compatibilidad

- La web muestra las bases en Web Mercator (`EPSG:3857`), mientras la entrada y los límites geográficos interoperables con QGIS y Google Earth usan WGS 84 (`EPSG:4326`). Son sistemas distintos, pero compatibles si se declaran y transforman explícitamente.
- Para cálculos de área o distancia se escogerá un CRS proyectado apropiado por AOI; `EPSG:32717` solo aplica al experimento de Riobamba y no debe aplicarse a Canadá o Estados Unidos.
- Al exportar desde Earth Engine se fijarán CRS, `crsTransform`/resolución, región y nodata. Al abrir cada archivo con Rasterio se validarán CRS, extensión y alineación antes de combinarlo con otra fecha.

## Fases recomendadas

1. Elegir una variable y un AOI de prueba; confirmar producto, licencia, rango temporal y escala.
2. Generar dos o tres GeoTIFF/COG reproducibles fuera de la web, con manifiesto y validación de CRS.
3. Construir en backend una lectura local de catálogo, límites de fecha y vista de una capa real.
4. Añadir comparación espacial real por píxel y, solo si hay series completas, control temporal/animación.
5. Incorporar clasificación supervisada únicamente con muestras y métricas auditables.

## Fuentes técnicas consultadas

- NASA POWER, API temporal: <https://power.larc.nasa.gov/docs/services/api/temporal/>.
- Google Earth Engine, exportación de imágenes y control explícito de proyección: <https://developers.google.com/earth-engine/guides/exporting_images>.
- Google Earth Engine, descarga de fragmentos pequeños: <https://developers.google.com/earth-engine/apidocs/ee-image-getdownloadurl>.
- NASA LP DAAC / AppEEARS, subconjuntos espaciales y salidas GeoTIFF o NetCDF-4: <https://lpdaac.usgs.gov/documents/534/AGC_Workshop_presentation_final_distribution.pdf>.
