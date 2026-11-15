import React, { useEffect, useMemo, useState } from 'react'
import { ImageOverlay, MapContainer, TileLayer, useMap } from 'react-leaflet'
import { api } from '../services/api'
import { useI18n } from '../i18n'
import 'leaflet/dist/leaflet.css'

const previewUrl = id => `/api/tif-lab/preview/${id}`
const formatBytes = value => value < 1_000_000 ? `${Math.round(value / 1000)} kB` : `${(value / 1_000_000).toFixed(2)} MB`
const assetLabel = asset => `${asset.year} · ${asset.layer} · ${asset.collection}`

function FitRaster({ bounds }) {
  const map = useMap()
  useEffect(() => { if (bounds) map.fitBounds(bounds, { padding: [18, 18], animate: false }) }, [map, bounds])
  return null
}

function RasterMap({ asset, imageUrl }) {
  const { t } = useI18n()
  if (!asset || !imageUrl) return null
  const [west, south, east, north] = asset.bounds
  const bounds = [[south, west], [north, east]]
  return <section className="tif-map-card"><MapContainer className="tif-map" bounds={bounds} scrollWheelZoom><FitRaster bounds={bounds}/><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/><ImageOverlay url={imageUrl} bounds={bounds} opacity={.72}/></MapContainer><p>{t('lab.previewNote')}</p></section>
}

function Metadata({ inspection }) {
  const { number, t } = useI18n()
  if (!inspection) return <div className="tif-empty">{t('lab.selectFile')}</div>
  const [west, south, east, north] = inspection.bounds
  return <section className="tif-metadata" aria-label={t('lab.metadata', { name: inspection.file_name })}><div className="tif-meta-header"><span className="tif-kicker">{t('lab.localTiff')}</span><b>{inspection.year} · {inspection.layer}</b><small>{inspection.collection}</small></div><dl><div><dt>{t('lab.grid')}</dt><dd>{inspection.shape[1]} × {inspection.shape[0]} · {inspection.dtype}</dd></div><div><dt>CRS</dt><dd>{inspection.epsg ? `EPSG:${inspection.epsg}` : inspection.crs || t('lab.notDeclared')}</dd></div><div><dt>{t('lab.bands')}</dt><dd>{inspection.band_count} · {inspection.kind === 'unverified_raster' ? t('lab.unverified') : t('lab.layerCodes')}</dd></div><div><dt>{t('lab.resolution')}</dt><dd>{inspection.resolution_degrees.map(value => value.toFixed(7)).join('° × ')}°</dd></div><div><dt>{t('lab.extent')}</dt><dd>{west.toFixed(4)}, {south.toFixed(4)} / {east.toFixed(4)}, {north.toFixed(4)}</dd></div><div><dt>{t('lab.noData')}</dt><dd>{number(inspection.nodata_pixels)} · {t('lab.code')} {inspection.nodata ?? t('lab.notDeclared')}</dd></div></dl><p>{inspection.interpretation}</p></section>
}

function Histogram({ inspection }) {
  const { number, t } = useI18n()
  if (!inspection) return null
  if (inspection.kind === 'unverified_raster') return <section className="tif-histogram"><div><span className="tif-kicker">{t('lab.technicalSummary')}</span><h2>{t('lab.undeclaredValues')}</h2><p>{inspection.sampled_for_summary ? t('lab.sampled') : t('lab.fullRead')}</p></div><div className="tif-code-list"><div><b>{t('lab.minimum')}</b><span>{inspection.value_summary?.minimum ?? '—'}</span></div><div><b>{t('lab.maximum')}</b><span>{inspection.value_summary?.maximum ?? '—'}</span></div><div><b>{t('lab.mean')}</b><span>{inspection.value_summary?.mean ?? '—'}</span></div><div><b>{t('lab.standardDeviation')}</b><span>{inspection.value_summary?.standard_deviation ?? '—'}</span></div></div></section>
  return <section className="tif-histogram"><div><span className="tif-kicker">{t('lab.distribution')}</span><h2>{t('lab.storedCodes')}</h2><p>{t('lab.validRange', { min: inspection.minimum_code ?? '—', max: inspection.maximum_code ?? '—' })}</p></div><div className="tif-code-list">{inspection.histogram.slice(0, 12).map(item => <div key={item.code}><b>{t('lab.codeLabel', { code: item.code })}</b><span>{item.percent_valid}% · {number(item.pixels)} píxeles</span></div>)}</div></section>
}

export function TifLab() {
  const { dynamic, number, t } = useI18n()
  const [items, setItems] = useState([])
  const [collectionId, setCollectionId] = useState('')
  const [beforeId, setBeforeId] = useState('')
  const [afterId, setAfterId] = useState('')
  const [beforeInspection, setBeforeInspection] = useState(null)
  const [afterInspection, setAfterInspection] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showMap, setShowMap] = useState(false)
  const [mapSource, setMapSource] = useState('before')
  const [warnings, setWarnings] = useState([])

  useEffect(() => {
    api.get('/tif-lab/catalog').then(({ items: received, warnings: receivedWarnings = [] }) => {
      setItems(received)
      setWarnings(receivedWarnings)
      const prepared = received.filter(item => item.collection === 'Ecu Cp').sort((a, b) => a.year - b.year)
      const defaultItems = prepared.length ? prepared : received.filter(item => item.layer === 'LC_Type5')
      const first = defaultItems[0] || received[0]
      const last = defaultItems.at(-1) || received.at(-1)
      setCollectionId(prepared.length ? 'Ecu Cp' : '')
      setBeforeId(first?.id || '')
      setAfterId(last?.id === first?.id ? defaultItems.at(-2)?.id || '' : last?.id || '')
    }).catch(() => setError(t('lab.catalogError')))
  }, [])

  const collections = useMemo(() => [...new Set(items.map(item => item.collection))], [items])
  const visibleItems = useMemo(() => collectionId ? items.filter(item => item.collection === collectionId) : items, [items, collectionId])
  const beforeAsset = useMemo(() => items.find(item => item.id === beforeId), [items, beforeId])
  const afterAsset = useMemo(() => items.find(item => item.id === afterId), [items, afterId])
  const compatibleAfter = useMemo(() => beforeAsset ? visibleItems.filter(item => item.layer === beforeAsset.layer) : visibleItems, [visibleItems, beforeAsset])

  useEffect(() => {
    let active = true
    if (!beforeId) { setBeforeInspection(null); return () => { active = false } }
    setBeforeInspection(null)
    api.get(`/tif-lab/inspect/${beforeId}`).then(value => { if (active) setBeforeInspection(value) }).catch(() => { if (active) setError(t('lab.beforeError')) })
    return () => { active = false }
  }, [beforeId])
  useEffect(() => {
    let active = true
    if (!afterId) { setAfterInspection(null); return () => { active = false } }
    setAfterInspection(null)
    api.get(`/tif-lab/inspect/${afterId}`).then(value => { if (active) setAfterInspection(value) }).catch(() => { if (active) setError(t('lab.afterError')) })
    return () => { active = false }
  }, [afterId])

  function setBefore(nextId) {
    setBeforeId(nextId)
    const next = visibleItems.find(item => item.id === nextId)
    if (next && !visibleItems.some(item => item.id === afterId && item.layer === next.layer && item.id !== nextId)) {
      const replacement = visibleItems.filter(item => item.layer === next.layer && item.id !== nextId).at(-1)
      setAfterId(replacement?.id || '')
    }
    setComparison(null)
  }

  function chooseCollection(nextCollection) {
    setCollectionId(nextCollection)
    const scoped = nextCollection ? items.filter(item => item.collection === nextCollection) : items
    const first = scoped[0]
    const sameLayer = first ? scoped.filter(item => item.layer === first.layer) : []
    const last = sameLayer.at(-1)
    setBeforeId(first?.id || '')
    setAfterId(last?.id === first?.id ? sameLayer.at(-2)?.id || '' : last?.id || '')
    setComparison(null)
  }

  async function compare() {
    if (!beforeId || !afterId) return
    setBusy(true); setError(''); setComparison(null)
    try { setComparison(await api.post('/tif-lab/compare', { before_id: beforeId, after_id: afterId })) } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const mapAsset = mapSource === 'after' ? afterAsset : beforeAsset
  const mapImage = mapSource === 'difference' && comparison ? comparison.comparison_preview_url : previewUrl(mapAsset?.id || '')
  const activeMapAsset = mapSource === 'difference' ? beforeAsset : mapAsset

  const [titleFirst, titleSecond] = t('lab.title').split('|')
  return <main className="tif-lab"><header className="tif-lab-header"><div><span className="tif-kicker">{t('lab.route')}</span><h1>{titleFirst} <em>{titleSecond}</em></h1><p>{t('lab.intro')}</p></div><span className="tif-url">/laboratorio-tif</span></header>
    {error && <div className="tif-error" role="alert">{dynamic(error)}</div>}
    <section className="tif-controls" aria-label={t('lab.filesAria')}><label>{t('lab.localFolder')}<select value={collectionId} onChange={event => chooseCollection(event.target.value)}><option value="">{t('lab.allFolders')}</option>{collections.map(collection => <option key={collection} value={collection}>{collection}</option>)}</select></label><label>{t('lab.fileA')}<select value={beforeId} onChange={event => setBefore(event.target.value)}>{visibleItems.map(item => <option key={item.id} value={item.id}>{assetLabel(item)}</option>)}</select></label><label>{t('lab.fileB')} <small>{t('lab.sameLayer')}</small><select value={afterId} onChange={event => { setAfterId(event.target.value); setComparison(null) }}>{compatibleAfter.map(item => <option key={item.id} value={item.id}>{assetLabel(item)}</option>)}</select></label><button onClick={compare} disabled={busy || !beforeId || !afterId || beforeId === afterId}>{busy ? t('lab.comparing') : t('lab.compare')} <span>→</span></button></section>
    <p className="tif-catalog-note">{t('lab.visible', { visible: visibleItems.length, total: items.length })}</p>{warnings.map(warning => <p key={warning} className="tif-catalog-note">{t('common.warning')}: {dynamic(warning)}</p>)}
    <section className="tif-previews"><article><div className="tif-preview-heading"><span>{t('lab.fileA')}</span><b>{beforeAsset ? `${beforeAsset.year} · ${beforeAsset.layer}` : '—'}</b><small>{beforeAsset ? formatBytes(beforeAsset.size_bytes) : ''}</small></div>{beforeAsset && <img src={previewUrl(beforeAsset.id)} alt={t('lab.previewAlt', { name: beforeAsset.file_name })}/>}<Metadata inspection={beforeInspection}/><Histogram inspection={beforeInspection}/></article><article><div className="tif-preview-heading"><span>{t('lab.fileB')}</span><b>{afterAsset ? `${afterAsset.year} · ${afterAsset.layer}` : '—'}</b><small>{afterAsset ? formatBytes(afterAsset.size_bytes) : ''}</small></div>{afterAsset && <img src={previewUrl(afterAsset.id)} alt={t('lab.previewAlt', { name: afterAsset.file_name })}/>}<Metadata inspection={afterInspection}/><Histogram inspection={afterInspection}/></article></section>
    <section className="tif-map-toggle"><label><input type="checkbox" checked={showMap} onChange={event => setShowMap(event.target.checked)}/> {t('lab.showMap')}</label>{showMap && <div className="tif-map-tabs"><button className={mapSource === 'before' ? 'active' : ''} onClick={() => setMapSource('before')}>{t('lab.fileA')}</button><button className={mapSource === 'after' ? 'active' : ''} onClick={() => setMapSource('after')}>{t('lab.fileB')}</button>{comparison && <button className={mapSource === 'difference' ? 'active' : ''} onClick={() => setMapSource('difference')}>{t('lab.difference')}</button>}</div>}{showMap && <RasterMap asset={activeMapAsset} imageUrl={mapImage}/>}</section>
    {comparison && <section className="tif-comparison"><div><span className="tif-kicker">{t('lab.directCompare')}</span><h2>{comparison.statistics.changed_code_percent}%</h2><p>{t('lab.changedText', { before: comparison.before.year, after: comparison.after.year })}</p></div><dl><div><dt>{t('lab.valid')}</dt><dd>{number(comparison.statistics.valid_pixels)}</dd></div><div><dt>{t('lab.changedCode')}</dt><dd>{number(comparison.statistics.changed_code_pixels)}</dd></div><div><dt>{t('lab.unchanged')}</dt><dd>{number(comparison.statistics.unchanged_pixels)}</dd></div><div><dt>{t('lab.excludedNodata')}</dt><dd>{number(comparison.statistics.excluded_nodata_pixels)}</dd></div></dl><div className="tif-transitions"><b>{t('lab.transitions')}</b>{comparison.top_transitions.length ? comparison.top_transitions.map(item => <span key={`${item.from_code}-${item.to_code}`}>{item.from_code} → {item.to_code}: {item.percent_valid}% ({number(item.pixels)})</span>) : <span>{t('lab.noChanges')}</span>}</div></section>}
  </main>
}
