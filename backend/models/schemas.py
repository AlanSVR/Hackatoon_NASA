from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.core.catalog import EARTH_TRENDS_MAX_YEAR, EARTH_TRENDS_MIN_YEAR


class PointRequest(BaseModel):
    country_id: str = Field(default='ecuador', min_length=2, max_length=64)
    region_id: str | None = Field(default=None, max_length=128)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode='after')
    def complete_coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('latitude y longitude deben enviarse juntas.')
        if self.latitude is None and not self.region_id:
            raise ValueError('Selecciona un punto en el mapa antes de consultar.')
        return self


class TimeSeriesRequest(PointRequest):
    provider_id: Literal['nasa_power'] = 'nasa_power'
    variable_id: str = Field(default='t2m', min_length=2, max_length=64)
    start_year: int = Field(default=EARTH_TRENDS_MIN_YEAR, ge=EARTH_TRENDS_MIN_YEAR, le=EARTH_TRENDS_MAX_YEAR)
    end_year: int = Field(default=EARTH_TRENDS_MAX_YEAR, ge=EARTH_TRENDS_MIN_YEAR, le=EARTH_TRENDS_MAX_YEAR)
    frequency: Literal['monthly'] = 'monthly'

    @model_validator(mode='after')
    def valid_period(self):
        if self.start_year > self.end_year:
            raise ValueError('start_year debe ser menor o igual que end_year.')
        return self


class AnomalyRequest(TimeSeriesRequest):
    baseline_start_year: int = Field(default=2021, ge=EARTH_TRENDS_MIN_YEAR, le=EARTH_TRENDS_MAX_YEAR)
    baseline_end_year: int = Field(default=2023, ge=EARTH_TRENDS_MIN_YEAR, le=EARTH_TRENDS_MAX_YEAR)

    @model_validator(mode='after')
    def valid_baseline(self):
        if self.baseline_start_year > self.baseline_end_year:
            raise ValueError('El inicio de la climatología debe preceder a su fin.')
        if self.baseline_start_year < self.start_year or self.baseline_end_year > self.end_year:
            raise ValueError('La climatología de referencia debe estar incluida en el período solicitado.')
        return self


class CompareRequest(TimeSeriesRequest):
    year_a: int = Field(default=2021, ge=EARTH_TRENDS_MIN_YEAR, le=EARTH_TRENDS_MAX_YEAR)
    year_b: int = Field(default=2025, ge=EARTH_TRENDS_MIN_YEAR, le=EARTH_TRENDS_MAX_YEAR)

    @model_validator(mode='after')
    def valid_comparison_years(self):
        if self.year_a == self.year_b:
            raise ValueError('Selecciona dos años diferentes para comparar.')
        if not (self.start_year <= self.year_a <= self.end_year and self.start_year <= self.year_b <= self.end_year):
            raise ValueError('Los años comparados deben pertenecer al período solicitado.')
        return self
