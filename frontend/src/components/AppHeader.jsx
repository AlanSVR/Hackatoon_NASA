import React from 'react'

export function AppHeader({ view, onViewChange, backendOk, onAbout }) {
  return <header className="app-header">
    <button className="brand" onClick={() => onViewChange('trends')} aria-label="Ir a AndesSAR Earth Trends"><span className="brand-mark" aria-hidden="true"><i/><i/><i/></span><span><b>AndesSAR</b><small>EARTH TRENDS</small></span></button>
    <nav aria-label="Navegación principal"><button className={view === 'trends' ? 'nav-link active' : 'nav-link'} onClick={() => onViewChange('trends')}>Tendencias</button><button className={view === 'sar' ? 'nav-link active' : 'nav-link'} onClick={() => onViewChange('sar')}>SAR experimental</button></nav>
    <div className="header-actions"><span className={`connection ${backendOk ? 'online' : 'offline'}`}><i/>{backendOk ? 'API local conectada' : 'API local sin conexión'}</span><button className="icon-button" onClick={onAbout} aria-label="Acerca de AndesSAR Earth Trends">?</button></div>
  </header>
}
