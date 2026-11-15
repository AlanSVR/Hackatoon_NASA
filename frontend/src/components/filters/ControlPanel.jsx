import React from 'react'
import { BASE_MAPS } from '../../config/map'
import { useI18n } from '../../i18n'

function Field({ label, children, detail }) { return <label className="field"><span>{label}</span>{children}{detail && <small>{detail}</small>}</label> }

export function ControlPanel({ filters, countries, regions, variables, busy, selection, onChange, onRun, onReset }) {
  const { t } = useI18n()
  const set = (key, value) => onChange({ ...filters, [key]: value })
  const pointLabel = selection?.type === 'point' ? t('trends.queryPoint', { lat: selection.latitude.toFixed(4), lon: selection.longitude.toFixed(4) }) : selection?.type === 'rectangle' || selection?.type === 'polygon' ? t('trends.savedArea') : t('trends.referencePoint')
  const [heroFirst, heroSecond] = t('trends.hero').split('|')
  return <aside className="control-panel" aria-label={t('trends.configure')}>
    <div className="panel-intro"><span className="eyebrow">{t('trends.configure')}</span><h1>{heroFirst}<br/><em>{heroSecond}</em></h1><p>{t('trends.source')}</p></div>
    <div className="filter-stack">
      <div className="section-label"><span>01</span> {t('trends.placeVariable')}</div>
      <Field label={t('trends.country')}><select value={filters.country_id} onChange={e => { const countryId = e.target.value; const firstRegion = regions.find(region => region.country_id === countryId); onChange({ ...filters, country_id: countryId, region_id: firstRegion?.id || '' }) }}>{countries.map(country => <option key={country.id} value={country.id}>{country.name}</option>)}</select></Field>
      <Field label={t('trends.region')}><select value={filters.region_id} onChange={e => set('region_id', e.target.value)}>{regions.filter(region => region.country_id === filters.country_id).map(region => <option key={region.id} value={region.id}>{region.name}</option>)}</select></Field>
      <Field label={t('trends.variable')}><select value={filters.variable_id} onChange={e => set('variable_id', e.target.value)}>{variables.map(variable => <option key={variable.id} value={variable.id}>{variable.short_name} · {variable.unit}</option>)}</select></Field>
      <div className="source-note"><span className="source-dot"/>{t('trends.sourceNote')} <small>{t('trends.availability')}</small></div>
      <div className="section-label"><span>02</span> {t('trends.period')}</div>
      <div className="two-fields"><Field label={t('trends.from')}><input type="number" min="1981" max="2025" value={filters.start_year} onChange={e => set('start_year', Number(e.target.value))}/></Field><Field label={t('trends.to')}><input type="number" min="1981" max="2025" value={filters.end_year} onChange={e => set('end_year', Number(e.target.value))}/></Field></div>
      <div className="resolution"><span>{t('trends.resolution')}</span><b>{t('trends.monthly')}</b><small>{t('trends.annualAggregation')}</small></div>
      <div className="section-label"><span>03</span> {t('trends.mapArea')}</div>
      <Field label={t('trends.baseMap')}><select value={filters.base_map} onChange={e => set('base_map', e.target.value)}>{Object.values(BASE_MAPS).map(map => <option key={map.id} value={map.id}>{t(map.labelKey)}</option>)}</select></Field>
      <div className="tool-grid" role="group" aria-label={t('trends.selectionTools')}>{[['point', '●', 'point'], ['rectangle', '▭', 'rectangle'], ['polygon', '⬠', 'polygon']].map(([mode, icon, key]) => <button key={mode} type="button" className={filters.selection_mode === mode ? 'tool selected' : 'tool'} onClick={() => set('selection_mode', mode)}><b>{icon}</b>{t(`trends.${key}`)}</button>)}</div>
      <p className="selection-copy">{pointLabel}</p>
    </div>
    <div className="panel-actions"><button className="run-button" onClick={onRun} disabled={busy}>{busy ? t('trends.querying') : t('trends.analyze')} <span>→</span></button><button className="reset-button" onClick={onReset}>{t('trends.reset')}</button></div>
  </aside>
}
