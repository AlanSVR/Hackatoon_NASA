import React from 'react'
import { useI18n } from '../i18n'

export function AppHeader({ view, onViewChange, backendOk, onAbout }) {
  const { language, setLanguage, t } = useI18n()
  return <header className="app-header">
    <button className="brand" onClick={() => onViewChange('trends')} aria-label={t('nav.goHome')}><span className="brand-mark" aria-hidden="true"><i/><i/><i/></span><span><b>AndesSAR</b><small>EARTH TRENDS</small></span></button>
    <nav aria-label={t('nav.mainNavigation')}><button className={view === 'trends' ? 'nav-link active' : 'nav-link'} onClick={() => onViewChange('trends')}>{t('nav.trends')}</button><button className={view === 'geoportal' ? 'nav-link active' : 'nav-link'} onClick={() => onViewChange('geoportal')}>{t('nav.geoportal')}</button><button className={view === 'comparison' ? 'nav-link active' : 'nav-link'} onClick={() => onViewChange('comparison')}>{t('nav.comparison')}</button></nav>
    <div className="header-actions"><span className={`connection ${backendOk ? 'online' : 'offline'}`}><i/>{backendOk ? t('nav.apiOnline') : t('nav.apiOffline')}</span><div className="language-switcher" role="group" aria-label={t('nav.language')}><button type="button" className={language === 'es' ? 'active' : ''} onClick={() => setLanguage('es')} aria-pressed={language === 'es'}>ES</button><span aria-hidden="true">|</span><button type="button" className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')} aria-pressed={language === 'en'}>EN</button></div><button className="icon-button" onClick={onAbout} aria-label={t('nav.about')}>?</button></div>
  </header>
}
