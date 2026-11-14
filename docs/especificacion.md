# Especificación funcional y no funcional

## Fuente documental pendiente

El prompt pide convertir `docs/Requsitos.pdf` en esta especificación. En la revisión del paquete no existe ese PDF ni otro archivo PDF. Por integridad, este documento sintetiza únicamente el prompt maestro y marca la conversión del PDF como pendiente; debe actualizarse cuando se entregue el original.

## Funcional

- Seleccionar Ecuador, Estados Unidos o Canadá y una de las localidades configuradas.
- Mostrar un mapa Leaflet con mapas base documentados, controles de zoom, punto/rectángulo/polígono y limpieza de selección.
- Solicitar series mensuales puntuales de NASA POWER mediante FastAPI para variables declaradas.
- Mostrar serie original, anomalías con período base explícito, agregados anuales, tendencia lineal, IC 95 %, p y advertencias.
- Comparar dos años sin denominar la diferencia una tendencia estadísticamente significativa.
- Conservar selección y filtros durante el cambio de paneles, y permitir restablecerlos.
- Exportar los resultados realmente devueltos por la API.
- Conservar la comparación SAR como módulo experimental y claramente separado.

## No funcional

- La API local escucha en `127.0.0.1`; no se exponen credenciales ni se aceptan URLs arbitrarias de proveedores.
- Consultas externas con timeout, errores comprensibles y caché TTL local.
- Validación Pydantic de fechas, coordenadas, país, región y combinaciones de comparación.
- Datos faltantes, procedencia, unidades y limitaciones quedan visibles en las respuestas.
- Diseño responsive, semántico y con contraste suficiente; ningún color es el único indicador de estado.
- El análisis no fabrica capas, clasificaciones, promedios espaciales ni causalidad.
