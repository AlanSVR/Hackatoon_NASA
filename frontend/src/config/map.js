export const BASE_MAPS = {
  osm: { id: 'osm', labelKey: 'maps.osm', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', crs: 'EPSG:3857' },
  satellite: { id: 'satellite', labelKey: 'maps.satellite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community', crs: 'EPSG:3857' },
  topo: { id: 'topo', labelKey: 'maps.topo', url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="https://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)', crs: 'EPSG:3857' },
  dark: { id: 'dark', labelKey: 'maps.dark', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri — Esri, DeLorme, NAVTEQ', crs: 'EPSG:3857' },
  light: { id: 'light', labelKey: 'maps.light', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri — Esri, DeLorme, NAVTEQ', crs: 'EPSG:3857' },
}

export const INITIAL_FILTERS = { country_id: 'ecuador', region_id: '', variable_id: 't2m', start_year: 2021, end_year: 2026, year_a: 2021, year_b: 2025, base_map: 'osm', selection_mode: 'point' }
