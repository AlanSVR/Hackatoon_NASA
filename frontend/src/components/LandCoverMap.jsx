import React, { useEffect, useMemo, useState } from 'react'
import { GeoJSON, ImageOverlay, MapContainer, Rectangle, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { BASE_MAPS } from '../config/map'
import 'leaflet/dist/leaflet.css'

function boundsForGeometry(geometry) {
  const points = []
  const visit = value => {
    if (!Array.isArray(value)) return
    if (typeof value[0] === 'number') { points.push(value); return }
    value.forEach(visit)
  }
  visit(geometry?.coordinates)
  if (!points.length) return null
  const longitudes = points.map(([longitude]) => longitude); const latitudes = points.map(([, latitude]) => latitude)
  return [[Math.min(...latitudes), Math.min(...longitudes)], [Math.max(...latitudes), Math.max(...longitudes)]]
}

function FitExtent({ bounds, selectedFeatures }) {
  const map = useMap()
  useEffect(() => { if (bounds) map.fitBounds(bounds, { padding: [22, 22], animate: false }) }, [map, bounds])
  const selectedBounds = useMemo(() => {
    const all = selectedFeatures.map(item => boundsForGeometry(item.geometry)).filter(Boolean)
    if (!all.length) return null
    return [[Math.min(...all.map(item => item[0][0])), Math.min(...all.map(item => item[0][1]))], [Math.max(...all.map(item => item[1][0])), Math.max(...all.map(item => item[1][1]))]]
  }, [selectedFeatures])
  useEffect(() => { if (selectedBounds) map.fitBounds(selectedBounds, { padding: [34, 34], animate: true, duration: .35 }) }, [map, selectedBounds])
  return null
}

function RefreshSize({ active }) {
  const map = useMap()
  useEffect(() => {
    if (active) window.setTimeout(() => map.invalidateSize({ animate: false }), 0)
  }, [active, map])
  return null
}

function Interaction({ mode, onInspect, onArea }) {
  const [corner, setCorner] = useState(null)
  useEffect(() => { setCorner(null) }, [mode])
  useMapEvents({
    click(event) {
      const { lat, lng } = event.latlng
      if (mode === 'inspect') { onInspect?.({ latitude: lat, longitude: lng }); return }
      if (mode !== 'area') return
      if (!corner) { setCorner({ latitude: lat, longitude: lng }); return }
      onArea?.([
        Math.min(corner.longitude, lng), Math.min(corner.latitude, lat),
        Math.max(corner.longitude, lng), Math.max(corner.latitude, lat),
      ])
      setCorner(null)
    },
  })
  return null
}

function ProvinceLayer({ areas, selectedIds, language, onToggle }) {
  const selected = useMemo(() => new Set(selectedIds), [selectedIds])
  const style = feature => selected.has(String(feature.properties?.area_id))
    ? { color: '#f59e0b', weight: 2.5, fillColor: '#fbbf24', fillOpacity: .18 }
    : { color: '#244f63', weight: 1, fillColor: '#2d7890', fillOpacity: .025 }
  const onEachFeature = (feature, layer) => {
    const properties = feature.properties || {}
    layer.bindTooltip(properties[`name_${language}`] || properties.name_es || properties.area_id, { sticky: true, direction: 'top' })
    layer.on({
      click(event) {
        event.originalEvent?.stopPropagation()
        onToggle?.(String(properties.area_id))
      },
      mouseover(event) { event.target.setStyle({ weight: 2, fillOpacity: .11 }) },
      mouseout(event) { event.target.setStyle(style(feature)) },
    })
  }
  // Remounting after a selection prevents Leaflet from retaining stale styles
  // on an older GeoJSON layer when selection mode changes.
  const key = `${language}:${selectedIds.slice().sort().join(',') || 'none'}`
  return areas?.features?.length ? <GeoJSON key={key} data={areas} style={style} onEachFeature={onEachFeature}/> : null
}

export function LandCoverMap({
  asset, mode = 'display', area, onInspect, onArea, administrativeAreas,
  selectedAreaIds = [], onToggleArea, language = 'es', secondaryAsset = null,
  blend = 0, compact = false, baseMap = 'osm', active = true,
}) {
  const coordinates = asset?.extent?.coordinates?.[0]
  if (!coordinates?.length) return null
  const longitudes = coordinates.map(([longitude]) => longitude)
  const latitudes = coordinates.map(([, latitude]) => latitude)
  const bounds = [[Math.min(...latitudes), Math.min(...longitudes)], [Math.max(...latitudes), Math.max(...longitudes)]]
  const selection = area ? [[area[1], area[0]], [area[3], area[2]]] : null
  const selectedFeatures = (administrativeAreas?.features || []).filter(feature => selectedAreaIds.includes(String(feature.properties?.area_id)))
  const firstUrl = `/api/geospatial/assets/${asset.asset_id}/land-cover/preview`
  const secondUrl = secondaryAsset ? `/api/geospatial/assets/${secondaryAsset.asset_id}/land-cover/preview` : null
  const mapDefinition = BASE_MAPS[baseMap] || BASE_MAPS.osm
  return <div className={`landcover-map-wrap${compact ? ' compact' : ''}`}>
    <MapContainer className="landcover-map" bounds={bounds} scrollWheelZoom>
      <RefreshSize active={active}/>
      <FitExtent bounds={bounds} selectedFeatures={selectedFeatures}/>
      <TileLayer attribution={mapDefinition.attribution} url={mapDefinition.url}/>
      <ImageOverlay url={firstUrl} bounds={bounds} opacity={secondaryAsset ? .84 : .8}/>
      {secondUrl && <ImageOverlay url={secondUrl} bounds={bounds} opacity={Math.max(0, Math.min(1, blend)) * .88}/>} 
      <ProvinceLayer areas={administrativeAreas} selectedIds={selectedAreaIds} language={language} onToggle={onToggleArea}/>
      <Interaction mode={mode} onInspect={onInspect} onArea={onArea}/>
      {selection && <Rectangle bounds={selection} pathOptions={{ color: '#f9c977', weight: 2, dashArray: '5 6', fillOpacity: .08 }}/>} 
    </MapContainer>
  </div>
}
