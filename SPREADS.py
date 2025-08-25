"""Herramienta para calcular spreads de precios eléctricos.

Este script descarga precios horarios del mercado eléctrico español desde
la API de ESIOS y calcula spreads diarios y mensuales para apoyar la
operación de baterías. Antes de ejecutarlo, debe definirse la variable de
entorno ``TOKEN`` con un token válido de la API.
"""

import argparse
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests


def compute_spreads(start_date: datetime, end_date: datetime, horas: int):
    """Descarga datos de precios y genera gráficos de spreads.

    Parameters
    ----------
    start_date : datetime
        Fecha inicial del rango de análisis.
    end_date : datetime
        Fecha final del rango de análisis.
    horas : int
        Número de horas más baratas y más caras a comparar.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, plotly.graph_objects.Figure, plotly.graph_objects.Figure]
        DataFrames con spreads diarios y mensuales y las figuras correspondientes.
    """

    indicador_tecnologia = {
        "1295": "Generación T.Real FV [MWh]",
        "550": "Generación T.Real Ciclo Combinado [MWh]",
        "551": "Generación T.Real Eólica [MWh]",
        "1294": "Generación T.Real CSP [MWh]",
        "1296": "Generación T.Real Biomasa [MWh]",
        "546": "Hidroeléctrica [MWh]",
        "600": "Precio mercado spot [€/MWh]",
    }

    indicador_SPOT = "600"
    indicador_actual = indicador_SPOT

    url_base = "https://api.esios.ree.es/"
    endpoint = "indicators/"
    url = url_base + endpoint + indicador_actual

    try:
        api_token = os.environ["TOKEN"]
    except KeyError as exc:
        raise EnvironmentError(
            "Debe definir la variable de entorno TOKEN con un token válido"
        ) from exc

    headers = {"Host": "api.esios.ree.es", "x-api-key": api_token}
    params = {
        "start_date": start_date.strftime("%Y-%m-%dT00:00"),
        "end_date": end_date.strftime("%Y-%m-%dT23:59"),
        "groupby": "hour",
    }

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
    except requests.exceptions.RequestException as exc:  # pragma: no cover - network
        raise RuntimeError(f"Error al obtener datos de la API: {exc}") from exc

    data = res.json()
    sheet_data = pd.DataFrame(data["indicator"]["values"])
    sheet_data = sheet_data[["datetime", "geo_name", "value"]]
    precio_col = indicador_tecnologia[indicador_actual]
    sheet_data = sheet_data.rename(
        columns={"datetime": f"datetime_{indicador_actual}", "value": precio_col}
    )

    sheet_data["datetime"] = pd.to_datetime(
        sheet_data[f"datetime_{indicador_actual}"].str.replace(r"\+.*$", "", regex=True),
        errors="coerce",
    )

    sheet_data["year"] = sheet_data["datetime"].dt.year
    sheet_data["day"] = sheet_data["datetime"].dt.date
    sheet_data["hour"] = sheet_data["datetime"].dt.hour

    hourly_avg_prices = (
        sheet_data.groupby(["year", "day", "hour", "geo_name"])[precio_col]
        .mean()
        .reset_index()
    )

    cheapest_hours = (
        hourly_avg_prices.groupby(["year", "day", "geo_name"])
        .apply(lambda x: x.nsmallest(horas, precio_col)[precio_col].mean())
        .reset_index(name="cheapest_avg")
    )

    expensive_hours = (
        hourly_avg_prices.groupby(["year", "day", "geo_name"])
        .apply(lambda x: x.nlargest(horas, precio_col)[precio_col].mean())
        .reset_index(name="expensive_avg")
    )

    daily_spread = pd.merge(
        cheapest_hours, expensive_hours, on=["year", "day", "geo_name"]
    )
    daily_spread["spread"] = (
        daily_spread["expensive_avg"] - daily_spread["cheapest_avg"]
    )

    daily_spread["month"] = pd.to_datetime(daily_spread["day"]).dt.to_period("M")
    monthly_spread = (
        daily_spread.groupby(["month", "geo_name"])["spread"].mean().reset_index()
    )
    monthly_spread["month"] = monthly_spread["month"].astype(str)

    fig_daily = px.line(
        daily_spread,
        x="day",
        y="spread",
        color="geo_name",
        title="Spread Diario para Operaciones de Batería por País",
        labels={"day": "Día", "spread": "Spread (€)", "geo_name": "País"},
        markers=True,
        color_discrete_sequence=px.colors.sequential.Blues,
    )
    fig_daily.update_layout(
        xaxis=dict(tickangle=45),
        yaxis_title=f"Spread de {horas} horas (€/MWh)",
        legend_title="País",
        template="plotly_white",
        font=dict(family="Calibri"),
    )

    fig_monthly = px.bar(
        monthly_spread,
        x="month",
        y="spread",
        color="geo_name",
        barmode="group",
        title="Spread Mensual Mercado Diario por País",
        labels={"month": "Mes", "spread": "Spread (€/MWh)", "geo_name": "País"},
        color_discrete_sequence=px.colors.sequential.Blues,
    )
    fig_monthly.update_layout(
        xaxis=dict(tickangle=45),
        yaxis_title=f"Spread de {horas} horas (€/MWh)",
        legend_title="País",
        template="plotly_white",
        font=dict(family="Calibri"),
    )

    return daily_spread, monthly_spread, fig_daily, fig_monthly


def main(start_date: datetime, end_date: datetime, horas: int) -> None:
    """Función de consola para mostrar los gráficos de spreads."""
    daily_spread, monthly_spread, fig_daily, fig_monthly = compute_spreads(
        start_date, end_date, horas
    )
    fig_daily.show()
    fig_monthly.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Calcula spreads diarios y mensuales a partir de precios horarios de ESIOS. "
            "Requiere definir la variable de entorno TOKEN."
        )
    )
    parser.add_argument(
        "--start-date", required=True, help="Fecha de inicio en formato YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", required=True, help="Fecha de fin en formato YYYY-MM-DD"
    )
    parser.add_argument(
        "--horas",
        type=int,
        default=6,
        help="Número de horas baratas y caras a comparar",
    )

    args = parser.parse_args()
    start = datetime.fromisoformat(args.start_date)
    end = datetime.fromisoformat(args.end_date)
    main(start, end, args.horas)
