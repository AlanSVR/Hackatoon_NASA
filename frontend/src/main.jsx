import { createRoot } from 'react-dom/client'
import React, { useEffect, useState } from 'react'
import './styles.css'
import { AppHeader } from './components/AppHeader'
import { AboutModal } from './components/AboutModal'
import { Geoportal } from './components/Geoportal'
import { LandCoverComparison } from './components/LandCoverComparison'
import { api } from './services/api'
import { I18nProvider } from './i18n'

function App({ initialView = 'geoportal' }) {
  const [view, setView] = useState(initialView)
  const [backendOk, setBackendOk] = useState(false)
  const [about, setAbout] = useState(false)

  useEffect(() => {
    api.get('/health').then(health => setBackendOk(Boolean(health.ok))).catch(() => setBackendOk(false))
  }, [])

  const switchView = nextView => {
    setView(nextView)
    const path = nextView === 'comparison' ? '/comparar' : '/'
    window.history.replaceState({}, '', path)
  }

  return <>
    <AppHeader view={view} onViewChange={switchView} backendOk={backendOk} onAbout={() => setAbout(true)}/>
    <div hidden={view !== 'geoportal'}><Geoportal active={view === 'geoportal'} onOpenComparison={() => switchView('comparison')}/></div>
    <div hidden={view !== 'comparison'}><LandCoverComparison active={view === 'comparison'} onBack={() => switchView('geoportal')}/></div>
    {about && <AboutModal onClose={() => setAbout(false)}/>}
  </>
}

const isComparisonRoute = /^\/(laboratorio-tif|comparar)\/?$/.test(window.location.pathname)
createRoot(document.getElementById('root')).render(<I18nProvider><App initialView={isComparisonRoute ? 'comparison' : 'geoportal'}/></I18nProvider>)
