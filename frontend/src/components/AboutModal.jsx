import React from 'react'
import { useI18n } from '../i18n'

export function AboutModal({ onClose }) {
  const { t } = useI18n()
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className="about-modal" role="dialog" aria-modal="true" aria-labelledby="about-title" onMouseDown={event => event.stopPropagation()}><button className="modal-close" onClick={onClose} aria-label={t('common.close')}>×</button><span className="eyebrow">ANDESSAR EARTH TRENDS</span><h2 id="about-title">{t('about.heading')}</h2><p>{t('about.intro')}</p><dl><div><dt>{t('about.challenge')}</dt><dd>NASA Space Apps Challenge 2026 · “Be An Earth System Trend Detective!”</dd></div><div><dt>{t('about.technologies')}</dt><dd>React, Leaflet, FastAPI, Rasterio, NumPy y SciPy.</dd></div><div><dt>{t('about.data')}</dt><dd>{t('about.dataValue')}</dd></div><div><dt>{t('about.team')}</dt><dd>{t('about.teamValue')}</dd></div></dl><p className="fine-print">{t('about.note')}</p></section></div>
}
