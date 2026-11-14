# Plan de implementación priorizado

1. **Auditoría y seguridad local — completada.** Diagnóstico, aislamiento temporal de PROJ y documentación de la base SAR.
2. **Núcleo científico — completado para NASA POWER.** Catálogos, consulta HTTP en backend, caché, validación, tendencia, anomalías, comparación y exportación.
3. **Interfaz Earth Trends — en esta entrega.** Panel de filtros, países, mapa base, estado de fuente, gráficos, resultados y descargas.
4. **Pruebas y endurecimiento — en esta entrega.** Pruebas unitarias de estadística y de rutas mediante respuesta NASA simulada; verificación de build de React y prueba de humo de API.
5. **Datos espaciales reales.** Añadir AppEEARS u otra retícula compatible, trabajos con progreso y tendencias por celda; solo entonces activar capas/animación espacial.
6. **Módulo de cobertura.** Incorporar entrenamiento, validación y productos de entrada antes de mostrar clases Páramo, antrópica, agropecuaria o forestal.

No se añaden Docker, PostGIS, Redis ni microservicios para este MVP local.
