import React from 'react'
import { useI18n } from '../i18n'

function Metric({ label, value, note }) {
  return <div><span>{label}</span><b>{value}</b>{note && <small>{note}</small>}</div>
}

export function CrsKpi({ crs }) {
  const { t } = useI18n()
  return <div className="asset-validation-kpis one-item"><Metric label={t('validation.crs')} value={crs || t('validation.unknownCrs')}/></div>
}

export function MapAgreementKpis({ agreement }) {
  const { number, t } = useI18n()
  if (!agreement || !Number.isFinite(agreement.kappa)) return null
  return <section className="map-agreement-kpis">
    <div><span className="eyebrow">{t('validation.eyebrow')}</span><h3>{t('validation.title')}</h3><p>{t('validation.mapAgreementNote')}</p></div>
    <div className="report-validation-metrics">
      <Metric label={t('validation.observedAgreement')} value={`${number(agreement.observed_agreement * 100, { maximumFractionDigits: 2 })}%`} note={`${number(agreement.sample_pixels)} ${t('validation.validCells')}`}/>
      <Metric label={t('validation.reliability')} value={number(agreement.kappa, { maximumFractionDigits: 4 })}/>
      <Metric label={t('validation.margin')} value={`±${number(agreement.agreement_margin_95 * 100, { maximumFractionDigits: 3 })} pp`} note={t('validation.marginNote')}/>
      <Metric label={t('validation.expectedAgreement')} value={`${number(agreement.expected_agreement * 100, { maximumFractionDigits: 2 })}%`}/>
    </div>
    <details><summary>{t('validation.formula')}</summary><p>{t('validation.formulaNote', { po: number(agreement.observed_agreement, { maximumFractionDigits: 6 }), pe: number(agreement.expected_agreement, { maximumFractionDigits: 6 }), kappa: number(agreement.kappa, { maximumFractionDigits: 6 }) })}</p></details>
  </section>
}
