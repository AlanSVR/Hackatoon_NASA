# Especificación funcional vigente

La interfaz principal trabaja únicamente con Ecuador. Earth Trends admite el
intervalo 2021–2026, exige un punto elegido por la persona usuaria y consulta
NASA POWER para series mensuales reales. El mapa usa `EPSG:3857` para la vista
y WGS 84 (`EPSG:4326`) para las coordenadas enviadas al proveedor.

El Geoportal conserva activos GeoTIFF, permite editar título y contexto sin
alterar píxeles, inspeccionar clases por píxel, delimitar rectángulos y calcular
composición de cobertura sobre los píxeles válidos. También compara años que
coinciden en producto, CRS, dimensiones y transformación. Una comparación de
clases no se describe como evidencia causal de cambio de cobertura.

Las clases, porcentajes y colores se muestran únicamente para el perfil
MCD12Q1.061 LC_Type1 (IGBP) declarado al importar. Las provincias, índices
espectrales, máscaras u otras capas sólo se habilitarán cuando se incorpore una
fuente verificable para ellas; la aplicación no los inventa.
