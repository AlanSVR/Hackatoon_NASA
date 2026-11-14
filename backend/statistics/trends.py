from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date
from statistics import mean
from typing import Any

from scipy import stats

MIN_MONTHS_FOR_MEAN_YEAR = 9
MIN_YEARS_FOR_TREND = 8


def _date(raw: str) -> date:
    return date.fromisoformat(raw)


def calculate_anomalies(observations: list[dict], baseline_start: int, baseline_end: int) -> dict[str, Any]:
    by_month: dict[int, list[float]] = defaultdict(list)
    for item in observations:
        if item['value'] is None:
            continue
        when = _date(item['date'])
        if baseline_start <= when.year <= baseline_end:
            by_month[when.month].append(float(item['value']))
    climatology = {month: round(mean(values), 6) for month, values in sorted(by_month.items()) if values}
    anomalies: list[dict] = []
    for item in observations:
        when = _date(item['date'])
        value = item['value']
        reference = climatology.get(when.month)
        anomalies.append({
            'date': item['date'],
            'value': None if value is None or reference is None else round(float(value) - reference, 6),
        })
    return {
        'baseline': {'start_year': baseline_start, 'end_year': baseline_end, 'monthly_climatology': climatology},
        'observations': anomalies,
        'note': 'Anomalía = valor mensual menos la climatología del mismo mes de referencia.',
    }


def annual_aggregate(observations: list[dict], variable: dict) -> tuple[list[dict], str, str]:
    buckets: dict[int, list[tuple[date, float]]] = defaultdict(list)
    for item in observations:
        if item['value'] is not None:
            when = _date(item['date'])
            buckets[when.year].append((when, float(item['value'])))

    series: list[dict] = []
    precipitation = variable['annual_aggregation'] == 'precip_rate_to_annual_total'
    for year, values in sorted(buckets.items()):
        if precipitation:
            # POWER devuelve mm/día para cada mes; se convierte en acumulado
            # mensual usando los días reales antes de sumar el año completo.
            annual_value = sum(value * monthrange(when.year, when.month)[1] for when, value in values)
            complete = len(values) == 12
            series.append({'year': year, 'value': round(annual_value, 4) if complete else None, 'months': len(values)})
        else:
            complete = len(values) >= MIN_MONTHS_FOR_MEAN_YEAR
            series.append({'year': year, 'value': round(mean(value for _, value in values), 4) if complete else None, 'months': len(values)})
    unit = 'mm/año' if precipitation else variable['unit']
    aggregation = ('Suma anual tras convertir cada media mensual en mm/mes; exige 12 meses válidos.' if precipitation
                   else f'Media anual; exige al menos {MIN_MONTHS_FOR_MEAN_YEAR} meses válidos.')
    return series, unit, aggregation


def calculate_trend(observations: list[dict], variable: dict) -> dict[str, Any]:
    annual, annual_unit, aggregation = annual_aggregate(observations, variable)
    valid = [item for item in annual if item['value'] is not None]
    result: dict[str, Any] = {
        'annual_series': annual,
        'annual_unit': annual_unit,
        'aggregation': aggregation,
        'n_annual_observations': len(valid),
        'minimum_required_years': MIN_YEARS_FOR_TREND,
        'method': 'Regresión lineal OLS sobre agregados anuales; prueba bilateral de pendiente.',
        'assumptions_and_limitations': [
            'La agregación anual reduce, pero no elimina necesariamente, estacionalidad y autocorrelación.',
            'El valor p e IC 95 % dependen de los supuestos OLS; no se ha aplicado aquí una corrección por autocorrelación.',
            'Una asociación temporal no demuestra causalidad.',
        ],
    }
    if len(valid) < MIN_YEARS_FOR_TREND:
        result.update({
            'status': 'insufficient_data', 'is_significant': None,
            'message': f'Se requieren al menos {MIN_YEARS_FOR_TREND} años agregados válidos; se obtuvieron {len(valid)}.',
            'slope_per_year': None, 'p_value': None, 'confidence_interval_95': None,
            'estimated_change': None,
        })
        return result

    x = [item['year'] for item in valid]
    y = [item['value'] for item in valid]
    regression = stats.linregress(x, y)
    degrees_of_freedom = len(valid) - 2
    critical = stats.t.ppf(0.975, degrees_of_freedom)
    margin = critical * regression.stderr
    p_value = float(regression.pvalue)
    significant = p_value < 0.05
    direction = 'positive' if regression.slope > 0 else 'negative' if regression.slope < 0 else 'flat'
    result.update({
        'status': f"{'significant' if significant else 'not_significant'}_{direction}",
        'is_significant': significant,
        'alpha': 0.05,
        'slope_per_year': round(float(regression.slope), 6),
        'slope_unit': f'{annual_unit}/año',
        'p_value': round(p_value, 6),
        'confidence_interval_95': [round(float(regression.slope - margin), 6), round(float(regression.slope + margin), 6)],
        'estimated_change': round(float(regression.slope * (max(x) - min(x))), 6),
        'estimated_change_unit': annual_unit,
        'message': ('La pendiente es estadísticamente significativa con α=0,05 bajo los supuestos indicados.' if significant
                    else 'La tendencia estimada no es estadísticamente significativa con α=0,05; es un resultado válido, no un error.'),
    })
    return result


def compare_years(observations: list[dict], variable: dict, year_a: int, year_b: int) -> dict[str, Any]:
    annual, unit, aggregation = annual_aggregate(observations, variable)
    index = {item['year']: item for item in annual}
    first, second = index.get(year_a), index.get(year_b)
    if not first or not second or first['value'] is None or second['value'] is None:
        return {
            'year_a': year_a, 'year_b': year_b, 'value_a': None, 'value_b': None, 'difference': None,
            'unit': unit, 'aggregation': aggregation,
            'message': 'No hay cobertura mensual suficiente para comparar ambos años.',
        }
    return {
        'year_a': year_a, 'year_b': year_b, 'value_a': first['value'], 'value_b': second['value'],
        'difference': round(second['value'] - first['value'], 6), 'unit': unit, 'aggregation': aggregation,
        'message': 'Es una diferencia entre años; no constituye una prueba de tendencia ni de significancia estadística.',
    }
