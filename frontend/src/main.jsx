import { createRoot } from 'react-dom/client'
import React, { useEffect, useMemo, useState } from 'react'
import './styles.css'
import { AppHeader } from './components/AppHeader'
import { AboutModal } from './components/AboutModal'
import { ControlPanel } from './components/filters/ControlPanel'
import { TrendMap } from './components/map/TrendMap'
import { ResultsPanel } from './components/results/ResultsPanel'
import { Geoportal } from './components/Geoportal'
import { LandCoverComparison } from './components/LandCoverComparison'
import { INITIAL_FILTERS } from './config/map'
import { api } from './services/api'
import { I18nProvider, useI18n } from './i18n'

function App() {
  const { t, dynamic } = useI18n()
  const [view, setView] = useState('trends')
  const [filters, setFilters] = useState(INITIAL_FILTERS)
  const [catalog, setCatalog] = useState({ countries: [], variables: [] })
  const [backendOk, setBackendOk] = useState(false)
  const [geometry, setGeometry] = useState(null)
  const [result, setResult] = useState(null)
  const [anomaly, setAnomaly] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [about, setAbout] = useState(false)

  useEffect(() => {
    Promise.all([api.get('/health'), api.get('/countries'), api.get('/variables')])
      .then(([health, countries, variables]) => { setBackendOk(Boolean(health.ok)); setCatalog({ countries, variables }) })
      .catch(() => setBackendOk(false))
  }, [])

  const country = useMemo(() => catalog.countries.find(item => item.id === filters.country_id), [catalog.countries, filters.country_id])

  async function runAnalysis() {
    setBusy(true); setError(''); setResult(null); setAnomaly(null); setComparison(null)
    const payload = { provider_id: 'nasa_power', country_id: filters.country_id, variable_id: filters.variable_id, start_year: filters.start_year, end_year: filters.end_year, frequency: 'monthly' }
    if (geometry?.type === 'point') { payload.latitude = geometry.latitude; payload.longitude = geometry.longitude }
    try {
      const trend = await api.post('/trends', payload)
      setResult(trend)
      const requests = [api.post('/compare', { ...payload, year_a: filters.year_a, year_b: filters.year_b })]
      if (filters.start_year <= 2021 && filters.end_year >= 2023) requests.push(api.post('/anomalies', { ...payload, baseline_start_year: 2021, baseline_end_year: Math.min(2023, filters.end_year) }))
      const settled = await Promise.all(requests)
      setComparison(settled[0]); setAnomaly(settled[1] || null)
    } catch (err) { setError(dynamic(err.message)) } finally { setBusy(false) }
  }

  function reset() { setFilters(INITIAL_FILTERS); setGeometry(null); setResult(null); setAnomaly(null); setComparison(null); setError('') }
  function download(format) { if (result?.export_id) window.open(`/api/exports/${result.export_id}?format=${format}`, '_blank', 'noopener,noreferrer') }

  return <>
    <AppHeader view={view} onViewChange={setView} backendOk={backendOk} onAbout={() => setAbout(true)}/>
    {view === 'geoportal' ? <Geoportal onOpenComparison={() => setView('comparison')}/> : view === 'comparison' ? <LandCoverComparison onBack={() => setView('geoportal')}/> : <main className="trends-workspace">
      <ControlPanel filters={filters} variables={catalog.variables} busy={busy} selection={geometry} onChange={setFilters} onRun={runAnalysis} onReset={reset}/>
      <section className="analysis-canvas">
        {error && <div className="error-banner" role="alert"><b>{t('trends.errorTitle')}</b><span>{error}</span></div>}
        <TrendMap country={country} region={null} filters={filters} geometry={geometry} onGeometry={setGeometry} onClearGeometry={() => setGeometry(null)} hasData={Boolean(result)}/>
        <ResultsPanel result={result} anomaly={anomaly} comparison={comparison} onDownload={download}/>
      </section>
    </main>}
    {about && <AboutModal onClose={() => setAbout(false)}/>}
  </>
}

function ComparisonPage() {
  const [backendOk, setBackendOk] = useState(false)
  const [about, setAbout] = useState(false)
  useEffect(() => { api.get('/health').then(health => setBackendOk(Boolean(health.ok))).catch(() => setBackendOk(false)) }, [])
  const navigate = view => { window.location.assign(view === 'comparison' ? '/laboratorio-tif' : '/') }
  return <><AppHeader view="comparison" backendOk={backendOk} onAbout={() => setAbout(true)} onViewChange={navigate}/><LandCoverComparison onBack={() => window.location.assign('/')}/>{about && <AboutModal onClose={() => setAbout(false)}/>}</>
}

const isTifLab = /^\/laboratorio-tif\/?$/.test(window.location.pathname)
createRoot(document.getElementById('root')).render(<I18nProvider>{isTifLab ? <ComparisonPage/> : <App />}</I18nProvider>)
