import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { ClassList } from './Geoportal'
import { LandCoverMap } from './LandCoverMap'
import { AssetValidationKpis, ReportValidationPanel } from './ClassificationValidation'
import { useI18n } from '../i18n'

const IGBP_PROFILE = 'mcd12q1_v061_lc_type1_igbp'

async function readJson(response, fallback) {
  const payload = await response.json().catch(() => null)
  if (response.ok) return payload
  throw new Error(typeof payload?.detail === 'string' ? payload.detail : fallback)
}

function Summary({ summary, title, language, number, t, asset }) {
  const stats = summary?.statistics
  if (!stats) return <section className="comparison-summary empty"><span>{t('common.loading')}</span></section>
  return <section className="comparison-summary">
    <span className="eyebrow">{title}</span>
    <div className="comparison-metrics">
      <div><span>{t('portal.validArea')}</span><b>{number(stats.valid_area_km2, { maximumFractionDigits: 2 })} km²</b></div>
      <div><span>{t('portal.waterClassArea')}</span><b>{number(stats.water_area_km2, { maximumFractionDigits: 2 })} km²</b></div>
      <div><span>{t('portal.validPixels')}</span><b>{number(stats.valid_pixels)}</b></div>
    </div>
    <ClassList classes={stats.classes} number={number} language={language} compact showArea/>
    <AssetValidationKpis asset={asset} crs={asset?.crs_text || (asset?.epsg ? `EPSG:${asset.epsg}` : null)}/>
  </section>
}

export function LandCoverComparison({ onBack }) {
  const { language, number, t, dynamic } = useI18n()
  const [assets, setAssets] = useState([])
  const [areas, setAreas] = useState(null)
  const [beforeId, setBeforeId] = useState('')
  const [afterId, setAfterId] = useState('')
  const [before, setBefore] = useState(null)
  const [after, setAfter] = useState(null)
  const [beforeSummary, setBeforeSummary] = useState(null)
  const [afterSummary, setAfterSummary] = useState(null)
  const [selectedAreaIds, setSelectedAreaIds] = useState([])
  const [comparison, setComparison] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [blend, setBlend] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)

  useEffect(() => {
    let alive = true
    Promise.all([
      fetch('/api/geospatial/assets').then(response => readJson(response, t('common.errorRequest'))),
      fetch('/api/geospatial/admin-areas?level=province').then(response => readJson(response, t('common.errorRequest'))),
    ]).then(([catalog, areaData]) => {
      if (!alive) return
      const classified = catalog.items.filter(item => item.declared_metadata?.analysis_profile === IGBP_PROFILE).sort((a, b) => String(a.captured_at || '').localeCompare(String(b.captured_at || '')))
      setAssets(classified); setAreas(areaData)
      if (classified.length) { setBeforeId(classified[0].asset_id); setAfterId(classified[classified.length - 1].asset_id) }
    }).catch(err => { if (alive) setError(dynamic(err.message)) })
    return () => { alive = false }
  }, [dynamic, t])

  useEffect(() => {
    let alive = true
    setBefore(null); setAfter(null); setBeforeSummary(null); setAfterSummary(null); setComparison(null); setBlend(0); setPlaying(false)
    if (!beforeId || !afterId) return () => { alive = false }
    Promise.all([
      fetch(`/api/geospatial/assets/${beforeId}`).then(response => readJson(response, t('common.errorRequest'))),
      fetch(`/api/geospatial/assets/${afterId}`).then(response => readJson(response, t('common.errorRequest'))),
    ]).then(([beforeAsset, afterAsset]) => { if (alive) { setBefore(beforeAsset); setAfter(afterAsset) } }).catch(err => { if (alive) setError(dynamic(err.message)) })
    return () => { alive = false }
  }, [beforeId, afterId, dynamic, t])

  const selectionRequest = useCallback((assetId) => selectedAreaIds.length
    ? fetch(`/api/geospatial/assets/${assetId}/land-cover/area`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ area_ids: selectedAreaIds }) })
    : fetch(`/api/geospatial/assets/${assetId}/land-cover`), [selectedAreaIds])

  useEffect(() => {
    let alive = true
    if (!beforeId || !afterId) return () => { alive = false }
    Promise.all([selectionRequest(beforeId), selectionRequest(afterId)])
      .then(async ([first, second]) => [await readJson(first, t('common.errorRequest')), await readJson(second, t('common.errorRequest'))])
      .then(([first, second]) => { if (alive) { setBeforeSummary(first); setAfterSummary(second) } })
      .catch(err => { if (alive) setError(dynamic(err.message)) })
    return () => { alive = false }
  }, [beforeId, afterId, selectionRequest, dynamic, t])

  useEffect(() => {
    if (!playing) return undefined
    const timer = window.setInterval(() => {
      setBlend(value => {
        const next = Math.min(1, value + (0.018 * speed))
        if (next >= 1) setPlaying(false)
        return next
      })
    }, 40)
    return () => window.clearInterval(timer)
  }, [playing, speed])

  const toggleProvince = areaId => {
    setSelectedAreaIds(current => current.includes(areaId) ? current.filter(item => item !== areaId) : [...current, areaId])
    setComparison(null); setBlend(0); setPlaying(false)
  }

  async function calculateComparison() {
    if (!beforeId || !afterId || beforeId === afterId) { setError(t('comparison.chooseDifferent')); return }
    setBusy(true); setError('')
    try {
      setComparison(await readJson(await fetch(`/api/geospatial/assets/${beforeId}/land-cover/compare`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ after_asset_id: afterId, ...(selectedAreaIds.length ? { area_ids: selectedAreaIds } : {}) }),
      }), t('common.errorRequest')))
    } catch (err) { setError(dynamic(err.message)) } finally { setBusy(false) }
  }

  const areaNames = useMemo(() => (areas?.features || []).filter(item => selectedAreaIds.includes(String(item.properties?.area_id))).map(item => item.properties?.[`name_${language}`] || item.properties?.name_es), [areas, selectedAreaIds, language])
  const labelFor = id => { const asset = assets.find(item => item.asset_id === id); return asset ? `${asset.captured_at || asset.original_name} · ${asset.declared_metadata?.map_title || asset.original_name}` : '' }
  const ready = before && after
  const canRestart = blend > 0 || playing
  const startPlayback = () => {
    if (playing) return
    if (blend >= 1) setBlend(0)
    setPlaying(true)
  }
  const restartPlayback = () => { setBlend(0); setPlaying(false) }

  const transitions = comparison?.comparison.transitions.map(item => ({
    code: `${item.from?.code}-${item.to?.code}`,
    label_es: `${item.from?.label_es || t('portal.unknownClass')} → ${item.to?.label_es || t('portal.unknownClass')}`,
    label_en: `${item.from?.label_en || t('portal.unknownClass')} → ${item.to?.label_en || t('portal.unknownClass')}`,
    color: item.to?.color || '#64748b', pixels: item.pixels, percent_valid: item.percent_valid,
  })) || []

  return <main className="comparison-workspace">
    <header className="comparison-header"><div><span className="eyebrow">{t('comparison.eyebrow')}</span><h1>{t('comparison.title')}</h1><p>{t('comparison.intro')}</p></div><button className="outline-button" onClick={onBack}>{t('comparison.backToGeoportal')}</button></header>
    {error && <div className="error-banner" role="alert"><b>{t('common.warning')}</b><span>{error}</span></div>}
    <section className="comparison-controls"><label>{t('comparison.firstMap')}<select value={beforeId} onChange={event => setBeforeId(event.target.value)}>{assets.map(asset => <option key={asset.asset_id} value={asset.asset_id}>{labelFor(asset.asset_id)}</option>)}</select></label><label>{t('comparison.secondMap')}<select value={afterId} onChange={event => setAfterId(event.target.value)}>{assets.map(asset => <option key={asset.asset_id} value={asset.asset_id}>{labelFor(asset.asset_id)}</option>)}</select></label><button onClick={calculateComparison} disabled={busy || !ready || beforeId === afterId}>{busy ? t('portal.rendering') : t('comparison.calculate')}</button></section>
    <p className="comparison-helper">{t('comparison.provinceHelp')}</p>
    {areaNames.length > 0 && <div className="province-selection"><b>{t('portal.provinceSelection')}</b><span>{areaNames.join(', ')}</span><button onClick={() => setSelectedAreaIds([])}>{t('portal.clearMapSelection')}</button></div>}
    {ready && <>
      <section className="processed-map-grid">
        <article><header><span>{t('comparison.firstProcessed')}</span><b>{labelFor(beforeId)}</b></header><LandCoverMap asset={before} mode="province" administrativeAreas={areas} selectedAreaIds={selectedAreaIds} onToggleArea={toggleProvince} language={language} compact/><Summary summary={beforeSummary} title={t('comparison.summary')} language={language} number={number} t={t} asset={before}/></article>
        <article><header><span>{t('comparison.secondProcessed')}</span><b>{labelFor(afterId)}</b></header><LandCoverMap asset={after} mode="province" administrativeAreas={areas} selectedAreaIds={selectedAreaIds} onToggleArea={toggleProvince} language={language} compact/><Summary summary={afterSummary} title={t('comparison.summary')} language={language} number={number} t={t} asset={after}/></article>
      </section>
      <ReportValidationPanel/>
      <section className="comparison-animation"><header><div><span className="eyebrow">{t('comparison.animation')}</span><h2>{t('comparison.transition')}</h2><p>{t('comparison.animationDisclosure')}</p></div><div className="animation-labels"><span>{before.captured_at || t('comparison.firstMap')}</span><b>{number(blend * 100, { maximumFractionDigits: 0 })}%</b><span>{after.captured_at || t('comparison.secondMap')}</span></div></header><LandCoverMap asset={before} secondaryAsset={after} blend={blend} mode="province" administrativeAreas={areas} selectedAreaIds={selectedAreaIds} onToggleArea={toggleProvince} language={language}/><div className="player-controls"><button onClick={restartPlayback} disabled={!canRestart} aria-label={t('comparison.restart')}>↺ {t('comparison.restart')}</button><button onClick={startPlayback} disabled={playing}>{playing ? t('comparison.playing') : `▶ ${t('comparison.play')}`}</button><input type="range" min="0" max="1" step="0.01" value={blend} disabled={playing} onChange={event => { setBlend(Number(event.target.value)); setPlaying(false) }} aria-label={t('comparison.transitionProgress')}/><span>{t('comparison.speed')}</span>{[0.5, 1, 2].map(value => <button key={value} className={speed === value ? 'active' : ''} disabled={playing} onClick={() => setSpeed(value)}>{value}×</button>)}</div></section>
      {comparison && blend >= 1 && <section className="comparison-result"><div><span className="eyebrow">{t('comparison.result')}</span><h2>{t('comparison.resultTitle')}</h2><p>{t('comparison.resultNote')}</p></div><div className="comparison-result-metrics"><div><span>{t('comparison.changedArea')}</span><b>{number(comparison.comparison.changed_area_km2, { maximumFractionDigits: 2 })} km²</b></div><div><span>{t('comparison.changedShare')}</span><b>{number(comparison.comparison.changed_percent, { maximumFractionDigits: 2 })}%</b></div><div><span>{t('comparison.changedPixels')}</span><b>{number(comparison.comparison.changed_pixels)}</b></div></div><ClassList classes={transitions} number={number} language={language} compact/><aside className="accuracy-note"><b>{t('comparison.accuracyTitle')}</b><span>{t('comparison.accuracyUnavailable')}</span></aside></section>}
      {comparison && blend < 1 && <p className="comparison-awaiting">{t('comparison.finishAnimation')}</p>}
    </>}
  </main>
}
