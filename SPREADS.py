"""BESS spread: cálculo de spreads de precios eléctricos.

Este script lee precios horarios del mercado eléctrico español desde el
archivo ``input.csv`` y calcula spreads diarios y mensuales para apoyar la
operación de baterías.
"""

import argparse
from datetime import datetime

from pathlib import Path

import pandas as pd
import plotly.express as px


def compute_spreads(start_date: datetime, end_date: datetime, horas: int):
    """Lee datos de precios y genera KPIs de spreads.

    La media de precios se calcula como media simple de los precios horarios
    filtrados por día y mes. La volatilidad es la desviación estándar de esos
    precios horarios, usada como indicador de riesgo.

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
    tuple[pd.DataFrame, pd.DataFrame, plotly.graph_objects.Figure,
          plotly.graph_objects.Figure]
        DataFrames con métricas diarias y mensuales y las figuras
        correspondientes.
    """

    precio_col = "Precio mercado spot [€/MWh]"
    data_path = Path(__file__).with_name("input.csv")
    sheet_data = pd.read_csv(data_path, sep=";")
    sheet_data["datetime"] = pd.to_datetime(
        sheet_data["datetime_600"].str.replace(r"\+.*$", "", regex=True),
        errors="coerce",
    )
    mask = (sheet_data["datetime"] >= start_date) & (
        sheet_data["datetime"] < end_date + pd.Timedelta(days=1)
    )
    sheet_data = sheet_data.loc[mask, ["datetime", "geo_name", precio_col]]

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

    # Precio medio diario por país (media simple de precios horarios)
    daily_avg = (
        hourly_avg_prices.groupby(["year", "day", "geo_name"])[precio_col]
        .mean()
        .reset_index(name="price_avg")
    )

    # Volatilidad diaria (desviación estándar de precios horarios)
    daily_volatility = (
        hourly_avg_prices.groupby(["year", "day", "geo_name"])[precio_col]
        .std()
        .reset_index(name="volatility")
    )

    # Combinar spreads, precio medio y volatilidad
    daily_stats = pd.merge(daily_spread, daily_avg, on=["year", "day", "geo_name"])
    daily_stats = pd.merge(
        daily_stats, daily_volatility, on=["year", "day", "geo_name"]
    )

    daily_stats["month"] = pd.to_datetime(daily_stats["day"]).dt.to_period("M")

    # Métricas mensuales
    monthly_spread = (
        daily_stats.groupby(["month", "geo_name"])["spread"].mean().reset_index()
    )
    monthly_avg = (
        daily_stats.groupby(["month", "geo_name"])["price_avg"]
        .mean()
        .reset_index()
    )
    monthly_volatility = (
        daily_stats.groupby(["month", "geo_name"])["volatility"]
        .mean()
        .reset_index()
    )

    monthly_stats = pd.merge(monthly_spread, monthly_avg, on=["month", "geo_name"])
    monthly_stats = pd.merge(
        monthly_stats, monthly_volatility, on=["month", "geo_name"]
    )
    monthly_stats["month"] = monthly_stats["month"].astype(str)

    fig_daily = px.line(
        daily_stats,
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
        monthly_stats,
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

    return (
        daily_stats,
        monthly_stats,
        fig_daily,
        fig_monthly,
    )


def main(start_date: datetime, end_date: datetime, horas: int) -> None:
    """Función de consola para mostrar los gráficos de spreads."""
    _, _, fig_daily, fig_monthly = compute_spreads(start_date, end_date, horas)
    fig_daily.show()
    fig_monthly.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calcula spreads diarios y mensuales a partir de precios horarios del archivo input.csv."
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
