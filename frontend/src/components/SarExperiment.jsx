import React, { useEffect, useState } from 'react'
import { ImageOverlay, MapContainer, Rectangle, TileLayer, useMapEvents } from 'react-leaflet'
import { useI18n } from '../i18n'
import 'leaflet/dist/leaflet.css'

const INITIAL_BBOX = [-78.705, -1.705, -78.625, -1.625]
const bounds = bbox => [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]

function SarPicker({ active, onSelect }) {
  const [first, setFirst] = useState(null)
  useMapEvents({ click(event) { if (!active) return; if (!first) setFirst(event.latlng); else { onSelect([Math.min(first.lng, event.latlng.lng), Math.min(first.lat, event.latlng.lat), Math.max(first.lng, event.latlng.lng), Math.max(first.lat, event.latlng.lat)]); setFirst(null) } } })
  return null
}

export function SarExperiment() {
  const { dynamic, number, t } = useI18n()
  const [scenes, setScenes] = useState([]); const [before, setBefore] = useState(''); const [after, setAfter] = useState(''); const [bbox, setBbox] = useState(INITIAL_BBOX); const [drawing, setDrawing] = useState(false); const [result, setResult] = useState(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  useEffect(() => { fetch('/api/scenes').then(response => response.ok ? response.json() : Promise.reject()).then(items => { setScenes(items); setBefore(items[0]?.id || ''); setAfter(items.at(-1)?.id || '') }).catch(() => setError(t('sar.catalogError'))) }, [t])
  async function analyze() { setBusy(true); setError(''); setResult(null); try { const response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ before_id: before, after_id: after, bbox, threshold_db: 3 }) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || t('sar.rasterError')); setResult(data) } catch (err) { setError(dynamic(err.message)) } finally { setBusy(false) } }
  const [titleFirst, titleSecond] = t('sar.title').split('|')
  return <main className="sar-lab"><section className="sar-copy"><span className="eyebrow">{t('sar.eyebrow')}</span><h1>{titleFirst} <em>{titleSecond}</em></h1><p>{t('sar.intro')}</p><label>{t('sar.before')}<select value={before} onChange={event => setBefore(event.target.value)}>{scenes.map(scene => <option key={scene.id} value={scene.id}>{scene.date} · {scene.source}</option>)}</select></label><label>{t('sar.after')}<select value={after} onChange={event => setAfter(event.target.value)}>{scenes.map(scene => <option key={scene.id} value={scene.id}>{scene.date} · {scene.source}</option>)}</select></label><button onClick={() => setDrawing(value => !value)} className="outline-button">{drawing ? t('sar.cancel') : t('sar.select')}</button><button onClick={analyze} disabled={busy || !before || !after || before === after} className="run-button">{busy ? t('sar.processing') : t('sar.run')} <span>→</span></button>{error && <p className="inline-error">{error}</p>}{result && <div className="sar-result"><b>{number(result.statistics.changed_area_ha)} ha</b><span>{t('sar.changed')}</span><small>{dynamic(result.method.scope)}</small><small>{t('sar.calculationCrs', { crs: result.method.crs_analysis, resolution: result.method.resolution_m })}</small></div>}</section><section className="sar-map"><MapContainer center={[-1.665, -78.665]} zoom={12} className="trend-map"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/><SarPicker active={drawing} onSelect={next => { setBbox(next); setDrawing(false); setResult(null) }}/><Rectangle bounds={bounds(bbox)} pathOptions={{ color: '#f9c977', dashArray: '5 7', fillOpacity: .05 }}/>{result && <ImageOverlay url={result.overlay_png} bounds={bounds(result.overlay_bounds)} opacity={.85}/>}</MapContainer><div className="map-coordinate-system sar-coordinate-system"><b>VISUALIZACIÓN EPSG:3857</b><span>Selección WGS 84 · EPSG:4326</span></div><div className="map-legend"><b>{t('sar.interpretation')}</b><p>{t('sar.interpretationText')}</p></div></section></main>
}
