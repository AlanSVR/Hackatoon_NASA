import React, { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../i18n'

async function readJson(response, fallback) {
  const payload = await response.json().catch(() => null)
  if (response.ok) return payload
  throw new Error(typeof payload?.detail === 'string' ? payload.detail : fallback)
}

function tokenHeaders(token) {
  return token ? { 'X-Geoportal-Token': token } : {}
}

export function Geoportal() {
  const { date, dynamic, number, t } = useI18n()
  const formatBytes = value => value < 1_000_000
    ? `${number(value / 1024, { maximumFractionDigits: 0 })} KiB`
    : `${number(value / 1_048_576, { maximumFractionDigits: 1 })} MiB`
  const [status, setStatus] = useState(null)
  const [assets, setAssets] = useState([])
  const [selected, setSelected] = useState(null)
  const [file, setFile] = useState(null)
  const [token, setToken] = useState('')
  const [capturedAt, setCapturedAt] = useState('')
  const [product, setProduct] = useState('')
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setError('')
    try {
      const nextStatus = await readJson(await fetch('/api/geospatial/status'), t('common.errorRequest'))
      setStatus(nextStatus)
      if (!nextStatus.ready) { setAssets([]); return }
      const response = await readJson(await fetch('/api/geospatial/assets'), t('common.errorRequest'))
      setAssets(response.items)
    } catch (err) { setError(dynamic(err.message)) }
  }, [dynamic, t])

  useEffect(() => { refresh() }, [refresh])

  async function upload() {
    if (!file || !status?.ready || progress) return
    setError('')
    if (!['.tif', '.tiff', '.vrt', '.aux.xml'].some(extension => file.name.toLowerCase().endsWith(extension))) {
      setError(t('portal.onlyTiff')); return
    }
    if (file.size > status.max_upload_bytes) {
      setError(t('portal.tooLarge', { limit: formatBytes(status.max_upload_bytes) })); return
    }
    const lowerName = file.name.toLowerCase()
    const assetKind = lowerName.endsWith('.vrt') ? 'virtual' : lowerName.endsWith('.aux.xml') ? 'auxiliary' : 'raster'
    if (assetKind !== 'raster') {
      setError(t('portal.virtualNeedsParent')); return
    }
    try {
      setProgress({ value: 0, label: t('portal.createSession') })
      const session = await readJson(await fetch('/api/geospatial/uploads/sessions', {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...tokenHeaders(token) },
        body: JSON.stringify({
          file_name: file.name, total_bytes: file.size, asset_kind: assetKind,
          captured_at: capturedAt || null,
          declared_metadata: product ? { product_name: product } : {},
        }),
      }), t('common.errorRequest'))
      for (let index = 0; index < session.expected_chunks; index += 1) {
        const start = index * session.chunk_bytes
        const block = file.slice(start, Math.min(file.size, start + session.chunk_bytes))
        const body = await block.arrayBuffer()
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
      setSelected(completed.asset_id)
      setFile(null); setProgress(null)
      await refresh()
    } catch (err) { setProgress(null); setError(dynamic(err.message)) }
  }

  const selectedAsset = assets.find(item => item.asset_id === selected)
  const [titleFirst, titleSecond] = t('portal.title').split('|')
  return <main className="geoportal-workspace">
    <header className="geoportal-header"><div><span className="eyebrow">{t('portal.heading')}</span><h1>{titleFirst} <em>{titleSecond}</em></h1><p>{t('portal.intro')}</p></div><button className="outline-button" onClick={refresh}>{t('common.refresh')}</button></header>
    {error && <div className="error-banner" role="alert"><b>{t('portal.unavailable')}</b><span>{error}</span></div>}
    <section className="geoportal-status" aria-live="polite"><div><span>{t('portal.persistence')}</span><b className={status?.ready ? 'status-ready' : 'status-pending'}>{status?.ready ? t('portal.postgisReady') : t('portal.pending')}</b></div><div><span>{t('portal.uploadProtection')}</span><b>{status?.upload_protection || t('common.verify')}</b></div><div><span>{t('portal.fileLimit')}</span><b>{status ? formatBytes(status.max_upload_bytes) : '—'}</b></div><small>{status?.ready ? t('portal.activeAssets', { count: status.asset_count }) : dynamic(status?.reason || t('portal.checking'))}</small></section>
    <section className="geoportal-upload"><div><span className="eyebrow">{t('portal.ingestion')}</span><h2>{t('portal.uploadTitle')}</h2><p>{t('portal.uploadIntro')}</p></div><div className="geoportal-upload-fields"><label>{t('portal.geotiffFile')}<input type="file" accept=".tif,.tiff" onChange={event => setFile(event.target.files?.[0] || null)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.captureDate')}<input type="date" value={capturedAt} onChange={event => setCapturedAt(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.declaredProduct')}<input value={product} maxLength="120" placeholder={t('portal.productPlaceholder')} onChange={event => setProduct(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><label>{t('portal.uploadToken')}<input type="password" autoComplete="off" value={token} placeholder={t('portal.tokenPlaceholder')} onChange={event => setToken(event.target.value)} disabled={!status?.ready || Boolean(progress)}/></label><button onClick={upload} disabled={!status?.ready || !file || Boolean(progress)}>{progress ? `${progress.value}%` : t('portal.save')}</button></div>{progress && <div className="upload-progress"><i style={{ width: `${progress.value}%` }}/><span>{progress.label}</span></div>}</section>
    <section className="geoportal-catalog"><div className="geoportal-catalog-title"><div><span className="eyebrow">{t('portal.assetsAvailable')}</span><h2>{t('portal.catalogTitle')}</h2></div><small>{t('portal.completedOnly')}</small></div>{assets.length ? <div className="asset-list">{assets.map(asset => <button key={asset.asset_id} className={selected === asset.asset_id ? 'asset-row selected' : 'asset-row'} onClick={() => setSelected(asset.asset_id)}><span>{asset.original_name}</span><small>{asset.asset_kind} · {asset.band_count ?? '—'} {t('portal.bands')} · {asset.epsg ? `EPSG:${asset.epsg}` : t('portal.crsUndeclared')}</small><b>{formatBytes(asset.byte_size)}</b></button>)}</div> : <div className="geoportal-empty">{status?.ready ? t('portal.noAssets') : t('portal.configureDb')}</div>}{selectedAsset && <section className="asset-detail"><img src={`/api/geospatial/assets/${selectedAsset.asset_id}/preview`} alt={t('portal.previewAlt', { name: selectedAsset.original_name })}/><div><span className="eyebrow">{t('portal.technicalView')}</span><h3>{selectedAsset.original_name}</h3><p>{t('portal.grayscale')}</p><dl><div><dt>{t('portal.dimensions')}</dt><dd>{selectedAsset.width} × {selectedAsset.height}</dd></div><div><dt>{t('portal.resolution')}</dt><dd>{selectedAsset.resolution_x?.toPrecision(6)} × {selectedAsset.resolution_y?.toPrecision(6)}</dd></div><div><dt>{t('portal.declaredDate')}</dt><dd>{selectedAsset.captured_at ? date(selectedAsset.captured_at) : t('portal.notDeclared')}</dd></div><div><dt>{t('portal.hash')}</dt><dd>{selectedAsset.sha256.slice(0, 16)}…</dd></div></dl></div></section>}</section>
  </main>
}
