export const BASE_MAPS = {
  osm: { id: 'osm', label: 'OpenStreetMap', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' },
  satellite: { id: 'satellite', label: 'Satélite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community' },
  topo: { id: 'topo', label: 'Topográfico', url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="https://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)' },
  dark: { id: 'dark', label: 'Modo oscuro', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri — Esri, DeLorme, NAVTEQ' },
  light: { id: 'light', label: 'Modo claro', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', attribution: 'Tiles &copy; Esri — Esri, DeLorme, NAVTEQ' },
}

export const INITIAL_FILTERS = { country_id: 'ecuador', region_id: 'riobamba_chimborazo', variable_id: 't2m', start_year: 2001, end_year: 2025, year_a: 2020, year_b: 2025, base_map: 'dark', selection_mode: 'point' }
