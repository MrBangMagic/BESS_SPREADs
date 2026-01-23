"""BESSpread: cálculo de spreads de precios eléctricos.

Este script lee precios horarios del mercado eléctrico español desde la
API de ESIOS y calcula spreads diarios y mensuales para apoyar la
operación de baterías.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import requests
import json


def fetch_esios_data(
    start_date: datetime,
    end_date: datetime,
    time_trunc: str = "hour",
    api_key: str = "3d85e18f83f86de7a7865e959a812e9ed9423828abed12113c954d0888bece70",
) -> pd.DataFrame:
    """Obtiene datos de precios desde la API de ESIOS.

    Parameters
    ----------
    start_date : datetime
        Fecha inicial del rango de datos a obtener.
    end_date : datetime
        Fecha final del rango de datos a obtener.
    time_trunc : str, optional
        Intervalo de agregación: "hour" para horario, "fifteen_minutes" para 15 minutos.
        Por defecto "hour".
    api_key : str, optional
        Token de API de ESIOS. Por defecto usa un token preconfigurado.

    Returns
    -------
    pd.DataFrame
        DataFrame con columnas: datetime_600, geo_name, Precio mercado spot [€/MWh]
    """
    indicator = "600"

    # Calcular la diferencia en días
    date_diff = (end_date - start_date).days

    # Si el rango es mayor a 7 días, dividir en peticiones diarias para evitar timeout
    if date_diff > 7:
        all_data = []
        current_date = start_date

        while current_date <= end_date:
            # Hacer petición para un solo día
            day_data = _fetch_single_day_esios(
                current_date,
                time_trunc,
                api_key,
                indicator
            )
            if day_data is not None and not day_data.empty:
                all_data.append(day_data)

            # Avanzar al siguiente día
            current_date += timedelta(days=1)

        if not all_data:
            raise Exception("La API no devolvió datos para el rango de fechas solicitado")

        # Combinar todos los DataFrames
        df = pd.concat(all_data, ignore_index=True)
        return df

    # Para rangos pequeños (≤7 días), usar la petición original
    # Formatear fechas para la API
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    # Usar hora local española (sin Z al final) para evitar desfase horario
    url = (
        f"https://api.esios.ree.es/indicators/{indicator}"
        f"?start_date={start_date_str}T00%3A00%3A00"
        f"&end_date={end_date_str}T23%3A59%3A59"
        f"&time_trunc={time_trunc}"
    )

    headers = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    try:
        response = requests.get(url, headers=headers, timeout=(5, 120))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error al conectar con la API de ESIOS: {e}")

    try:
        r_object = json.loads(response.text)
        indicator_values = r_object["indicator"]["values"]
    except (json.JSONDecodeError, KeyError) as e:
        raise Exception(f"Error al procesar la respuesta de la API: {e}")

    if not indicator_values:
        raise Exception("La API no devolvió datos para el rango de fechas solicitado")

    df = pd.DataFrame(indicator_values)

    # Verificar que las columnas necesarias existan
    required_cols = ["datetime", "geo_name", "value"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise Exception(f"La respuesta de la API no contiene las columnas esperadas: {missing_cols}")

    df = df[["datetime", "geo_name", "value"]]
    df.columns = ["datetime_600", "geo_name", "Precio mercado spot [€/MWh]"]

    return df


def _fetch_single_day_esios(
    date: datetime,
    time_trunc: str,
    api_key: str,
    indicator: str = "600",
) -> Optional[pd.DataFrame]:
    """Obtiene datos de un solo día desde la API de ESIOS.

    Esta función auxiliar se usa para peticiones grandes que se dividen por día.

    Parameters
    ----------
    date : datetime
        Fecha del día a obtener.
    time_trunc : str
        Intervalo de agregación: "hour" o "fifteen_minutes".
    api_key : str
        Token de API de ESIOS.
    indicator : str, optional
        Indicador de ESIOS. Por defecto "600".

    Returns
    -------
    Optional[pd.DataFrame]
        DataFrame con los datos del día, o None si hay error.
    """
    date_str = date.strftime("%Y-%m-%d")

    url = (
        f"https://api.esios.ree.es/indicators/{indicator}"
        f"?start_date={date_str}T00%3A00%3A00"
        f"&end_date={date_str}T23%3A59%3A59"
        f"&time_trunc={time_trunc}"
    )

    headers = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    try:
        response = requests.get(url, headers=headers, timeout=(5, 120))
        response.raise_for_status()

        r_object = json.loads(response.text)
        indicator_values = r_object["indicator"]["values"]

        if not indicator_values:
            return None

        df = pd.DataFrame(indicator_values)

        # Verificar columnas
        required_cols = ["datetime", "geo_name", "value"]
        if not all(col in df.columns for col in required_cols):
            return None

        df = df[["datetime", "geo_name", "value"]]
        df.columns = ["datetime_600", "geo_name", "Precio mercado spot [€/MWh]"]

        return df

    except Exception as e:
        # En caso de error en un día específico, registrar y continuar
        print(f"Advertencia: Error al obtener datos para {date_str}: {e}")
        return None


def compute_spreads(
    start_date: datetime,
    end_date: datetime,
    horas: int,
    data: Optional[pd.DataFrame] = None,
    intervalo: str = "Horario",
):
    """Obtiene datos de precios desde la API de ESIOS y genera KPIs de spreads.

    La media de precios se calcula como media simple de los precios
    filtrados por día y mes. La volatilidad es la desviación estándar de esos
    precios, usada como indicador de riesgo.

    Parameters
    ----------
    start_date : datetime
        Fecha inicial del rango de análisis.
    end_date : datetime
        Fecha final del rango de análisis.
    horas : int
        Número de horas más baratas y más caras a comparar.
    data : pandas.DataFrame, optional
        Datos de precios ya cargados. Si es ``None`` se obtendrán desde la API de ESIOS.
    intervalo : str, optional
        Tipo de intervalo: "Horario" o "15 minutos". Por defecto "Horario".

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, plotly.graph_objects.Figure,
          plotly.graph_objects.Figure]
        DataFrames con métricas diarias y mensuales y las figuras
        correspondientes.
    """

    precio_col = "Precio mercado spot [€/MWh]"

    if data is None:
        # Obtener datos desde la API de ESIOS
        sheet_data = fetch_esios_data(start_date, end_date)
    else:
        sheet_data = data.copy()

    # Convertir datetime_600 a datetime, manejando tanto strings como timestamps
    sheet_data["datetime"] = pd.to_datetime(
        sheet_data["datetime_600"],
        errors="coerce",
    )

    # Verificar que la conversión fue exitosa antes de acceder a .dt
    if pd.api.types.is_datetime64_any_dtype(sheet_data["datetime"]):
        # Si tiene zona horaria, convertir a Europe/Madrid y luego remover tz info
        try:
            if sheet_data["datetime"].dt.tz is not None:
                sheet_data["datetime"] = sheet_data["datetime"].dt.tz_convert('Europe/Madrid').dt.tz_localize(None)
        except (AttributeError, TypeError):
            # Si hay algún error al acceder a la zona horaria, continuar sin conversión
            pass
    else:
        raise ValueError("No se pudo convertir la columna datetime_600 a tipo datetime")

    # Asegurar que el precio sea numérico
    sheet_data[precio_col] = pd.to_numeric(sheet_data[precio_col], errors="coerce")

    mask = (sheet_data["datetime"] >= start_date) & (
        sheet_data["datetime"] < end_date + pd.Timedelta(days=1)
    )
    sheet_data = sheet_data.loc[mask, ["datetime", "geo_name", precio_col]]

    sheet_data["year"] = sheet_data["datetime"].dt.year
    sheet_data["day"] = sheet_data["datetime"].dt.date

    # Crear columna de intervalo según el tipo seleccionado
    if intervalo == "15 minutos":
        # Para 15 minutos, crear un identificador único por cada intervalo del día
        sheet_data["interval"] = (
            sheet_data["datetime"].dt.hour * 4 + sheet_data["datetime"].dt.minute // 15
        )
        group_cols = ["year", "day", "interval", "geo_name"]
    else:
        # Para horario, usar la hora como identificador
        sheet_data["interval"] = sheet_data["datetime"].dt.hour
        group_cols = ["year", "day", "interval", "geo_name"]

    # Calcular precios promedio por intervalo
    interval_avg_prices = (
        sheet_data.groupby(group_cols)[precio_col]
        .mean()
        .reset_index()
    )

    # Calcular número de intervalos a comparar (ajustado según el intervalo)
    # Para horario: horas directamente
    # Para 15 minutos: horas * 4 (4 intervalos de 15 min por hora)
    num_intervals = horas if intervalo == "Horario" else horas * 4

    cheapest_intervals = (
        interval_avg_prices.groupby(["year", "day", "geo_name"])
        .apply(lambda x: x.nsmallest(num_intervals, precio_col)[precio_col].mean())
        .reset_index(name="cheapest_avg")
    )

    expensive_intervals = (
        interval_avg_prices.groupby(["year", "day", "geo_name"])
        .apply(lambda x: x.nlargest(num_intervals, precio_col)[precio_col].mean())
        .reset_index(name="expensive_avg")
    )

    daily_spread = pd.merge(
        cheapest_intervals, expensive_intervals, on=["year", "day", "geo_name"]
    )
    daily_spread["spread"] = (
        daily_spread["expensive_avg"] - daily_spread["cheapest_avg"]
    )

    # Precio medio diario por país (media simple de precios por intervalo)
    daily_avg = (
        interval_avg_prices.groupby(["year", "day", "geo_name"])[precio_col]
        .mean()
        .reset_index(name="price_avg")
    )

    # Volatilidad diaria (desviación estándar de precios por intervalo)
    daily_volatility = (
        interval_avg_prices.groupby(["year", "day", "geo_name"])[precio_col]
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
    month_ts = pd.PeriodIndex(monthly_stats["month"]).to_timestamp()
    spanish_months = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    month_names = month_ts.month.map(spanish_months)
    monthly_stats["month_name"] = month_names.str.capitalize() + " " + month_ts.year.astype(str)
    monthly_stats = monthly_stats.sort_values("month")
    monthly_stats["month"] = monthly_stats["month"].astype(str)

    # Determinar etiqueta según intervalo
    interval_label = "15 minutos" if intervalo == "15 minutos" else "horario"

    fig_daily = px.line(
        daily_stats,
        x="day",
        y="spread",
        color="geo_name",
        title=f"Spread Diario para Operaciones de Batería por País (Análisis {interval_label})",
        labels={"day": "Día", "spread": "Spread (€)", "geo_name": "País"},
        markers=True,
        color_discrete_sequence=px.colors.sequential.Blues,
    )
    fig_daily.update_layout(
        xaxis=dict(tickangle=45),
        yaxis_title=f"Spread de {horas} horas - análisis {interval_label} (€/MWh)",
        legend_title="País",
        template="plotly_white",
        font=dict(family="Calibri"),
    )

    country_colors = px.colors.qualitative.Plotly
    fig_monthly = px.bar(
        monthly_stats,
        x="month_name",
        y="spread",
        color="geo_name",
        text="geo_name",
        barmode="group",
        color_discrete_sequence=country_colors,
        title=f"Spread Mensual Mercado Diario por País (Análisis {interval_label})",
        labels={"month_name": "Mes", "spread": "Spread (€/MWh)", "geo_name": "País"},
    )
    fig_monthly.update_traces(textposition="outside")
    fig_monthly.update_layout(
        xaxis=dict(tickangle=0),
        yaxis_title=f"Spread de {horas} horas - análisis {interval_label} (€/MWh)",
        legend_title="País",
        template="plotly_white",
        font=dict(family="Calibri"),
        xaxis_tickfont_size=12,
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
        description="Calcula spreads diarios y mensuales a partir de precios horarios obtenidos desde la API de ESIOS."
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
