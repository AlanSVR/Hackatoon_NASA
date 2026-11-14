import React from 'react'
import { BASE_MAPS } from '../../config/map'

function Field({ label, children, detail }) { return <label className="field"><span>{label}</span>{children}{detail && <small>{detail}</small>}</label> }

export function ControlPanel({ filters, countries, regions, variables, busy, selection, onChange, onRun, onReset }) {
  const set = (key, value) => onChange({ ...filters, [key]: value })
  const pointLabel = selection?.type === 'point' ? `Punto de consulta: ${selection.latitude.toFixed(4)}, ${selection.longitude.toFixed(4)}` : selection?.type === 'rectangle' || selection?.type === 'polygon' ? 'Área dibujada guardada. NASA POWER analizará el punto configurado, no un promedio del área.' : 'Usando el punto de referencia de la localidad.'
  return <aside className="control-panel" aria-label="Parámetros de análisis">
    <div className="panel-intro"><span className="eyebrow">CONFIGURAR CONSULTA</span><h1>Encuentra la señal.<br/><em>Explica sus límites.</em></h1><p>NASA POWER · series mensuales de punto · análisis reproducible local.</p></div>
    <div className="filter-stack">
      <div className="section-label"><span>01</span> Lugar y variable</div>
      <Field label="País"><select value={filters.country_id} onChange={e => { const countryId = e.target.value; const firstRegion = regions.find(region => region.country_id === countryId); onChange({ ...filters, country_id: countryId, region_id: firstRegion?.id || '' }) }}>{countries.map(country => <option key={country.id} value={country.id}>{country.name}</option>)}</select></Field>
      <Field label="Región o localidad"><select value={filters.region_id} onChange={e => set('region_id', e.target.value)}>{regions.filter(region => region.country_id === filters.country_id).map(region => <option key={region.id} value={region.id}>{region.name}</option>)}</select></Field>
      <Field label="Variable ambiental"><select value={filters.variable_id} onChange={e => set('variable_id', e.target.value)}>{variables.map(variable => <option key={variable.id} value={variable.id}>{variable.short_name} · {variable.unit}</option>)}</select></Field>
      <div className="source-note"><span className="source-dot"/>Fuente: NASA POWER <small>La disponibilidad se valida al consultar.</small></div>
      <div className="section-label"><span>02</span> Período</div>
      <div className="two-fields"><Field label="Desde"><input type="number" min="1981" max="2025" value={filters.start_year} onChange={e => set('start_year', Number(e.target.value))}/></Field><Field label="Hasta"><input type="number" min="1981" max="2025" value={filters.end_year} onChange={e => set('end_year', Number(e.target.value))}/></Field></div>
      <div className="resolution"><span>Resolución</span><b>Mensual</b><small>Agregación anual para la prueba de tendencia.</small></div>
      <div className="section-label"><span>03</span> Mapa y zona</div>
      <Field label="Mapa base"><select value={filters.base_map} onChange={e => set('base_map', e.target.value)}>{Object.values(BASE_MAPS).map(map => <option key={map.id} value={map.id}>{map.label}</option>)}</select></Field>
      <div className="tool-grid" role="group" aria-label="Herramientas de selección">{[['point', '●', 'Punto'], ['rectangle', '▭', 'Rectángulo'], ['polygon', '⬠', 'Polígono']].map(([mode, icon, label]) => <button key={mode} type="button" className={filters.selection_mode === mode ? 'tool selected' : 'tool'} onClick={() => set('selection_mode', mode)}><b>{icon}</b>{label}</button>)}</div>
      <p className="selection-copy">{pointLabel}</p>
    </div>
    <div className="panel-actions"><button className="run-button" onClick={onRun} disabled={busy}>{busy ? 'Consultando NASA POWER…' : 'Analizar tendencias'} <span>→</span></button><button className="reset-button" onClick={onReset}>Restablecer filtros</button></div>
  </aside>
}
