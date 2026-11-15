import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { LandCoverMap } from './LandCoverMap'
import { CrsKpi } from './ClassificationValidation'
import { BASE_MAPS } from '../config/map'
import { useI18n } from '../i18n'

const IGBP_PROFILE = 'mcd12q1_v061_lc_type1_igbp'

async function readJson(response, fallback) {
  const payload = await response.json().catch(() => null)
  if (response.ok) return payload
  throw new Error(typeof payload?.detail === 'string' ? payload.detail : fallback)
}

function tokenHeaders(token) { return token ? { 'X-Geoportal-Token': token } : {} }

export function ClassList({ classes = [], number, language, compact = false, showArea = false }) {
  return <div className={compact ? 'landcover-class-list compact' : 'landcover-class-list'}>
    {classes.map(item => <div key={item.code}>
      <i style={{ background: item.color }}/>
      <span>{item[`label_${language}`] || item.label_es || item.label_en}</span>
      <b>{number(item.percent_valid, { maximumFractionDigits: 2 })}%</b>
      <small>{showArea && Number.isFinite(item.area_km2) ? `${number(item.area_km2, { maximumFractionDigits: 2 })} km² · ` : ''}{number(item.pixels)}</small>
    </div>)}
  </div>
}

function Metric({ label, value, note }) {
  return <div className="landcover-kpi"><span>{label}</span><b>{value}</b>{note && <small>{note}</small>}</div>
}

export function Geoportal({ onOpenComparison, active = true }) {
  const { date, dynamic, language, number, t } = useI18n()
  const [status, setStatus] = useState(null)
  const [assets, setAssets] = useState([])
  const [selected, setSelected] = useState(null)
  const [assetDetail, setAssetDetail] = useState(null)
  const [file, setFile] = useState(null)
  const [token, setToken] = useState('')
  const [capturedAt, setCapturedAt] = useState('')
  const [product, setProduct] = useState('')
  const [mapTitle, setMapTitle] = useState('')
  const [sourceNote, setSourceNote] = useState('')
  const [profile, setProfile] = useState('generic')
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState('')
  const [landcover, setLandcover] = useState(null)
  const [mapMode, setMapMode] = useState('province')
  const [pixel, setPixel] = useState(null)
  const [area, setArea] = useState(null)
  const [areaStats, setAreaStats] = useState(null)
  const [adminAreas, setAdminAreas] = useState(null)
  const [selectedAreaIds, setSelectedAreaIds] = useState([])
  const [provinceSelectionMode, setProvinceSelectionMode] = useState('single')
  const [baseMap, setBaseMap] = useState('osm')
  const [comparisonAsset, setComparisonAsset] = useState('')
  const [comparison, setComparison] = useState(null)
  const [analysisBusy, setAnalysisBusy] = useState(false)
  const [metadataBusy, setMetadataBusy] = useState(false)
  const [rgbBands, setRgbBands] = useState({ red_band: 1, green_band: 2, blue_band: 3 })
  const [capabilities, setCapabilities] = useState(null)
  const [analysisResult, setAnalysisResult] = useState(null)

  const formatBytes = value => value < 1_000_000
    ? `${number(value / 1024, { maximumFractionDigits: 0 })} KiB`
    : `${number(value / 1_048_576, { maximumFractionDigits: 1 })} MiB`

  const refresh = useCallback(async () => {
    setError('')
    try {
      const nextStatus = await readJson(await fetch('/api/geospatial/status'), t('common.errorRequest'))
      setStatus(nextStatus)
      setAssets(nextStatus.ready ? (await readJson(await fetch('/api/geospatial/assets'), t('common.errorRequest'))).items : [])
    } catch (err) { setError(dynamic(err.message)) }
  }, [dynamic, t])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    let alive = true
    fetch('/api/geospatial/admin-areas?level=province')
      .then(response => readJson(response, t('common.errorRequest')))
      .then(value => { if (alive) setAdminAreas(value) })
      .catch(err => { if (alive) setError(dynamic(err.message)) })
    return () => { alive = false }
  }, [dynamic, t])

  useEffect(() => {
    let alive = true
    setLandcover(null); setArea(null); setAreaStats(null); setPixel(null); setSelectedAreaIds([]); setComparison(null); setCapabilities(null); setAnalysisResult(null)
    if (!selected) { setAssetDetail(null); return () => { alive = false } }
    Promise.all([
      fetch(`/api/geospatial/assets/${selected}`).then(response => readJson(response, t('common.errorRequest'))),
      fetch(`/api/geospatial/assets/${selected}/analysis-capabilities`).then(response => readJson(response, t('common.errorRequest'))),
    ]).then(async ([detail, capability]) => {
      if (!alive) return
      setAssetDetail(detail); setCapabilities(capability)
      const bands = capability.bands.map(item => item.band_index)
      setRgbBands({ red_band: bands[0] || 1, green_band: bands[1] || bands[0] || 1, blue_band: bands[2] || bands[0] || 1 })
      const metadata = detail.declared_metadata || {}
      setMapTitle(metadata.map_title || ''); setSourceNote(metadata.source_note || '')
      if (metadata.analysis_profile === IGBP_PROFILE) {
        const summary = await fetch(`/api/geospatial/assets/${selected}/land-cover`).then(response => readJson(response, t('common.errorRequest')))
        if (alive) setLandcover(summary)
      }
    }).catch(err => { if (alive) setError(dynamic(err.message)) })
    return () => { alive = false }
    // The chosen asset, not translated copy, defines the analysis state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  async function upload() {
    if (!file || !status?.ready || progress) return
    const lowerName = file.name.toLowerCase()
    if (!['.tif', '.tiff'].some(extension => lowerName.endsWith(extension))) { setError(t('portal.onlyTiff')); return }
    if (file.size > status.max_upload_bytes) { setError(t('portal.tooLarge', { limit: formatBytes(status.max_upload_bytes) })); return }
    try {
      setError(''); setProgress({ value: 0, label: t('portal.createSession') })
      const declaredMetadata = {
        ...(product ? { product_name: product } : {}),
        ...(mapTitle ? { map_title: mapTitle } : {}),
        ...(sourceNote ? { source_note: sourceNote } : {}),
        ...(profile === IGBP_PROFILE ? { analysis_profile: IGBP_PROFILE, classification_system: 'IGBP Land Cover Type 1' } : {}),
      }
      const session = await readJson(await fetch('/api/geospatial/uploads/sessions', {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...tokenHeaders(token) },
        body: JSON.stringify({ file_name: file.name, total_bytes: file.size, asset_kind: 'raster', captured_at: capturedAt || null, declared_metadata: declaredMetadata }),
      }), t('common.errorRequest'))
      for (let index = 0; index < session.expected_chunks; index += 1) {
        const start = index * session.chunk_bytes
        const body = await file.slice(start, Math.min(file.size, start + session.chunk_bytes)).arrayBuffer()
        const headers = { 'Content-Type': 'application/octet-stream', ...tokenHeaders(token) }
        if (window.crypto?.subtle) {
          const digest = await window.crypto.subtle.digest('SHA-256', body)
          headers['X-Chunk-SHA256'] = Array.from(new Uint8Array(digest)).map(value => value.toString(16).padStart(2, '0')).join('')
        }
        setProgress({ value: Math.round(100 * index / session.expected_chunks), label: t('portal.uploadChunk', { current: index + 1, total: session.expected_chunks }) })
        await readJson(await fetch(session.put_chunk_url_template.replace('{chunk_index}', index), { method: 'PUT', headers, body }), t('common.errorRequest'))
      }
      setProgress({ value: 100, label: t('portal.validate') })
      const completed = await readJson(await fetch(session.complete_url, { method: 'POST', headers: tokenHeaders(token) }), t('common.errorRequest'))
      setSelected(completed.asset_id); setFile(null); setProgress(null); await refresh()
    } catch (err) { setProgress(null); setError(dynamic(err.message)) }
  }

  async function inspectPoint(point) {
    if (!selected) return
    try {
      setError(''); setSelectedAreaIds([]); setArea(null); setAreaStats(null)
      const params = new URLSearchParams({ longitude: point.longitude, latitude: point.latitude })
      setPixel(await readJson(await fetch(`/api/geospatial/assets/${selected}/land-cover/class-at?${params}`), t('common.errorRequest')))
    } catch (err) { setError(dynamic(err.message)) }
  }

  async function inspectArea(bbox) {
    if (!selected) return
    try {
      setError(''); setArea(bbox); setSelectedAreaIds([]); setPixel(null)
      setAreaStats(await readJson(await fetch(`/api/geospatial/assets/${selected}/land-cover/area`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bbox }) }), t('common.errorRequest')))
    } catch (err) { setError(dynamic(err.message)) }
  }

  async function toggleProvince(areaId) {
    if (!selected) return
    const nextIds = provinceSelectionMode === 'single'
      ? (selectedAreaIds.length === 1 && selectedAreaIds[0] === areaId ? [] : [areaId])
      : (selectedAreaIds.includes(areaId) ? selectedAreaIds.filter(item => item !== areaId) : [...selectedAreaIds, areaId])
    setSelectedAreaIds(nextIds); setArea(null); setPixel(null); setComparison(null); setError('')
    if (!nextIds.length) { setAreaStats(null); return }
    try {
      setAreaStats(await readJson(await fetch(`/api/geospatial/assets/${selected}/land-cover/area`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ area_ids: nextIds }) }), t('common.errorRequest')))
    } catch (err) { setError(dynamic(err.message)) }
  }

  async function compareLandCover() {
    if (!selected || !comparisonAsset) return
    setAnalysisBusy(true); setError('')
    try {
      const selection = selectedAreaIds.length ? { area_ids: selectedAreaIds } : area ? { bbox: area } : {}
      setComparison(await readJson(await fetch(`/api/geospatial/assets/${selected}/land-cover/compare`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ after_asset_id: comparisonAsset, ...selection }) }), t('common.errorRequest')))
    } catch (err) { setError(dynamic(err.message)) } finally { setAnalysisBusy(false) }
  }

  async function saveMetadata() {
    if (!selected || metadataBusy) return
    setMetadataBusy(true); setError('')
    try {
      await readJson(await fetch(`/api/geospatial/assets/${selected}/metadata`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ map_title: mapTitle, source_note: sourceNote }) }), t('common.errorRequest'))
      setAssetDetail(current => current ? { ...current, declared_metadata: { ...current.declared_metadata, map_title: mapTitle, source_note: sourceNote } } : current)
      await refresh()
    } catch (err) { setError(dynamic(err.message)) } finally { setMetadataBusy(false) }
  }

  async function runRgb() {
    if (!selected || analysisBusy) return
    setAnalysisBusy(true); setError('')
    try { setAnalysisResult(await readJson(await fetch(`/api/geospatial/assets/${selected}/renders/rgb`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rgbBands) }), t('common.errorRequest'))) } catch (err) { setError(dynamic(err.message)) } finally { setAnalysisBusy(false) }
  }

  const selectedAsset = assets.find(asset => asset.asset_id === selected)
  const comparableAssets = useMemo(() => assets.filter(asset => asset.asset_id !== selected && asset.declared_metadata?.analysis_profile === IGBP_PROFILE), [assets, selected])
  const stats = areaStats?.statistics || landcover?.statistics
  const selectedNames = (areaStats?.selection?.areas || []).map(item => item[`name_${language}`] || item.name_es)
  const [titleFirst, titleSecond] = t('portal.title').split('|')

  return <main className="geoportal-workspace">
    <header className="geoportal-header"><div><span className="eyebrow">{t('portal.heading')}</span><h1>{titleFirst} <em>{titleSecond}</em></h1><p>{t('portal.intro')}</p></div><button className="outline-button" onClick={refresh}>{t('common.refresh')}</button></header>
    {error && <div className="error-banner" role="alert"><b>{t('portal.unavailable')}</b><span>{error}</span></div>}
    <section className="geoportal-status" aria-live="polite"><div><span>{t('portal.persistence')}</span><b className={status?.ready ? 'status-ready' : 'status-pending'}>{status?.ready ? t('portal.postgisReady') : t('portal.pending')}</b></div><div><span>{t('portal.uploadProtection')}</span><b>{status?.upload_protection || t('common.verify')}</b></div><div><span>{t('portal.fileLimit')}</span><b>{status ? formatBytes(status.max_upload_bytes) : '—'}</b></div><small>{status?.ready ? t('portal.activeAssets', { count: status.asset_count }) : dynamic(status?.reason || t('portal.checking'))}</small></section>

    <section className="geoportal-upload"><div><span className="eyebrow">{t('portal.ingestion')}</span><h2>{t('portal.uploadTitle')}</h2><p>{t('portal.uploadIntro')}</p></div><div className="geoportal-upload-fields"><label>{t('portal.geotiffFile')}<input type="file" accept=".tif,.tiff" onChange={event => setFile(event.target.files?.[0] || null)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.captureDate')}<input type="date" value={capturedAt} onChange={event => setCapturedAt(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.declaredProduct')}<input value={product} maxLength="120" placeholder={t('portal.productPlaceholder')} onChange={event => setProduct(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.classificationProfile')}<select value={profile} onChange={event => setProfile(event.target.value)} disabled={!status?.ready || Boolean(progress)}><option value="generic">{t('portal.genericProfile')}</option><option value={IGBP_PROFILE}>{t('portal.igbpProfile')}</option></select></label><label>{t('portal.mapTitle')}<input value={mapTitle} maxLength="160" placeholder={t('portal.mapTitlePlaceholder')} onChange={event => setMapTitle(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.sourceNote')}<input value={sourceNote} maxLength="1200" placeholder={t('portal.sourceNotePlaceholder')} onChange={event => setSourceNote(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.uploadToken')}<input type="password" autoComplete="off" value={token} placeholder={t('portal.tokenPlaceholder')} onChange={event => setToken(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><button onClick={upload} disabled={!status?.ready || !file || Boolean(progress)}>{progress ? `${progress.value}%` : t('portal.save')}</button></div>{progress && <div className="upload-progress"><i style={{ width: `${progress.value}%` }}/><span>{progress.label}</span></div>}</section>

    <section className="geoportal-catalog"><div className="geoportal-catalog-title"><div><span className="eyebrow">{t('portal.assetsAvailable')}</span><h2>{t('portal.catalogTitle')}</h2></div><small>{t('portal.completedOnly')}</small></div>{assets.length ? <div className="asset-list">{assets.map(asset => <button key={asset.asset_id} className={selected === asset.asset_id ? 'asset-row selected' : 'asset-row'} onClick={() => setSelected(asset.asset_id)}><span>{asset.declared_metadata?.map_title || asset.original_name}</span><small>{asset.declared_metadata?.product_name || asset.asset_kind} · {asset.band_count ?? '—'} {t('portal.bands')} · {asset.epsg ? `EPSG:${asset.epsg}` : t('portal.crsUndeclared')}</small><b>{asset.captured_at || formatBytes(asset.byte_size)}</b></button>)}</div> : <div className="geoportal-empty">{status?.ready ? t('portal.noAssets') : t('portal.configureDb')}</div>}
      {selectedAsset && <section className="asset-detail"><img src={landcover ? `/api/geospatial/assets/${selectedAsset.asset_id}/land-cover/preview` : `/api/geospatial/assets/${selectedAsset.asset_id}/preview`} alt={t('portal.previewAlt', { name: selectedAsset.original_name })}/><div><span className="eyebrow">{landcover ? t('portal.classifiedView') : t('portal.technicalView')}</span><h3>{assetDetail?.declared_metadata?.map_title || selectedAsset.original_name}</h3><p>{landcover ? t('portal.igbpDescription') : t('portal.grayscale')}</p><dl><div><dt>{t('portal.dimensions')}</dt><dd>{selectedAsset.width} × {selectedAsset.height}</dd></div><div><dt>{t('portal.declaredDate')}</dt><dd>{selectedAsset.captured_at ? date(selectedAsset.captured_at) : t('portal.notDeclared')}</dd></div><div><dt>{t('portal.hash')}</dt><dd>{selectedAsset.sha256.slice(0, 16)}…</dd></div></dl></div></section>}
      {selectedAsset && <section className="metadata-editor"><div><span className="eyebrow">{t('portal.editor')}</span><h3>{t('portal.editorTitle')}</h3><p>{t('portal.editorNote')}</p></div><label>{t('portal.mapTitle')}<input value={mapTitle} onChange={event => setMapTitle(event.target.value)} maxLength="160"/></label><label>{t('portal.sourceNote')}<textarea value={sourceNote} onChange={event => setSourceNote(event.target.value)} maxLength="1200" rows="3"/></label><button onClick={saveMetadata} disabled={metadataBusy}>{metadataBusy ? t('portal.saving') : t('portal.saveContext')}</button></section>}
    </section>

    {landcover && selectedAsset && assetDetail && <section className="landcover-workspace"><header><div><span className="eyebrow">{t('portal.landCover')}</span><h2>{t('portal.landCoverTitle')}</h2><p>{t('portal.landCoverNote')}</p></div><div className="landcover-tools"><label className="map-style-control">{t('portal.baseMap')}<select value={baseMap} onChange={event => setBaseMap(event.target.value)}>{Object.values(BASE_MAPS).map(item => <option key={item.id} value={item.id}>{t(item.labelKey)}</option>)}</select></label><button className={mapMode === 'province' ? 'active' : ''} onClick={() => setMapMode('province')}>{t('portal.selectProvince')}</button><button className={provinceSelectionMode === 'single' ? 'active' : ''} onClick={() => { setProvinceSelectionMode('single'); setMapMode('province') }}>{t('portal.oneProvince')}</button><button className={provinceSelectionMode === 'multiple' ? 'active' : ''} onClick={() => { setProvinceSelectionMode('multiple'); setMapMode('province') }}>{t('portal.multipleProvinces')}</button><button className={mapMode === 'inspect' ? 'active' : ''} onClick={() => setMapMode('inspect')}>{t('portal.inspectPoint')}</button><button className={mapMode === 'area' ? 'active' : ''} onClick={() => setMapMode('area')}>{t('portal.delimitArea')}</button><button onClick={() => { setArea(null); setAreaStats(null); setPixel(null); setSelectedAreaIds([]) }}>{t('portal.clearMapSelection')}</button></div></header>
      <LandCoverMap asset={assetDetail} mode={mapMode} area={area} onInspect={inspectPoint} onArea={inspectArea} administrativeAreas={adminAreas} selectedAreaIds={selectedAreaIds} onToggleArea={toggleProvince} language={language} baseMap={baseMap} active={active}/>
      <p className="landcover-instruction">{mapMode === 'province' ? t('portal.provinceInstruction') : mapMode === 'inspect' ? t('portal.inspectInstruction') : t('portal.areaInstruction')}</p>
      {selectedNames.length > 0 && <div className="province-selection"><b>{t('portal.provinceSelection')}</b><span>{selectedNames.join(', ')}</span></div>}
      {stats && <><div className="landcover-kpis"><Metric label={t('portal.validPixels')} value={number(stats.valid_pixels)}/><Metric label={t('portal.validArea')} value={`${number(stats.valid_area_km2, { maximumFractionDigits: 2 })} km²`} note={t('portal.areaEstimateNote')}/><Metric label={t('portal.waterClassArea')} value={`${number(stats.water_area_km2, { maximumFractionDigits: 2 })} km²`} note={t('portal.waterClassNote')}/><Metric label={t('portal.selectionScope')} value={areaStats ? (selectedAreaIds.length ? t('portal.provinceSelection') : t('portal.selectedArea')) : t('portal.fullRaster')}/></div><CrsKpi crs={assetDetail.crs_text || (assetDetail.epsg ? `EPSG:${assetDetail.epsg}` : null)}/>
        {pixel && <div className="landcover-inspector"><span className="eyebrow">{t('portal.pixelInspector')}</span>{pixel.sample.nodata ? <p>{t('portal.nodataAtPoint')}</p> : <><i style={{ background: pixel.sample.class?.color }}/><b>{pixel.sample.class?.[`label_${language}`] || pixel.sample.class?.label_es || t('portal.unknownClass')}</b><span>{t('portal.codeValue', { code: pixel.sample.code })} · {number(pixel.sample.latitude, { maximumFractionDigits: 5 })}, {number(pixel.sample.longitude, { maximumFractionDigits: 5 })}</span></>}</div>}
        <div className="landcover-columns"><section><span className="eyebrow">{areaStats ? t('portal.areaComposition') : t('portal.classComposition')}</span><h3>{t('portal.coverDistribution')}</h3><ClassList classes={stats.classes} number={number} language={language} showArea={Boolean(areaStats)}/></section><section><span className="eyebrow">{t('portal.comparison')}</span><h3>{t('portal.compareYears')}</h3><label>{t('portal.compareWith')}<select value={comparisonAsset} onChange={event => { setComparisonAsset(event.target.value); setComparison(null) }}><option value="">{t('portal.chooseYear')}</option>{comparableAssets.map(asset => <option key={asset.asset_id} value={asset.asset_id}>{asset.captured_at || asset.original_name} · {asset.declared_metadata?.map_title || asset.original_name}</option>)}</select></label><button onClick={compareLandCover} disabled={!comparisonAsset || analysisBusy}>{analysisBusy ? t('portal.rendering') : t('portal.runComparison')}</button>{comparison && <div className="landcover-comparison-result"><b>{number(comparison.comparison.changed_percent, { maximumFractionDigits: 2 })}%</b><span>{t('portal.changedCodeShare')}</span><small>{number(comparison.comparison.changed_pixels)} / {number(comparison.comparison.valid_pixels)} {t('portal.validPixels').toLowerCase()}</small></div>}<button className="outline-button comparison-studio-link" onClick={onOpenComparison}>{t('portal.openComparisonStudio')}</button></section></div></>}
    </section>}

    {selectedAsset && !landcover && <section className="geoportal-analysis"><span className="eyebrow">{t('portal.analysis')}</span><h2>{t('portal.rgb')}</h2><p>{capabilities?.band_semantics === 'unverified' ? t('portal.analysisNote') : t('portal.grayscale')}</p><div className="geoportal-rgb"><label>{t('portal.red')}<select value={rgbBands.red_band} onChange={event => setRgbBands(value => ({ ...value, red_band: Number(event.target.value) }))}>{capabilities?.bands.map(band => <option key={band.band_index} value={band.band_index}>{band.band_index}</option>)}</select></label><label>{t('portal.green')}<select value={rgbBands.green_band} onChange={event => setRgbBands(value => ({ ...value, green_band: Number(event.target.value) }))}>{capabilities?.bands.map(band => <option key={band.band_index} value={band.band_index}>{band.band_index}</option>)}</select></label><label>{t('portal.blue')}<select value={rgbBands.blue_band} onChange={event => setRgbBands(value => ({ ...value, blue_band: Number(event.target.value) }))}>{capabilities?.bands.map(band => <option key={band.band_index} value={band.band_index}>{band.band_index}</option>)}</select></label><button onClick={runRgb} disabled={analysisBusy}>{analysisBusy ? t('portal.rendering') : t('portal.render')}</button></div>{analysisResult && <div className="geoportal-derived"><img src={analysisResult.image_url} alt={t('portal.analysisImageAlt', { name: selectedAsset.original_name })}/><p>{dynamic(analysisResult.note)}</p></div>}</section>}
  </main>
}
