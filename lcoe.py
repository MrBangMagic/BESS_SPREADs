"""LCOE: cálculo del Coste Nivelado de Energía para sistemas BESS.

Este módulo calcula el LCOE (Levelized Cost of Energy) para sistemas de
almacenamiento de energía con baterías (BESS), permitiendo evaluar la
rentabilidad de operaciones de arbitraje en el mercado eléctrico.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


@dataclass
class BESSParameters:
    """Parámetros del sistema de almacenamiento BESS.

    Attributes
    ----------
    power_capacity_mw : float
        Capacidad de potencia del sistema en MW.
    energy_capacity_mwh : float
        Capacidad de energía del sistema en MWh.
    capex_power : float
        CAPEX de potencia en €/kW (inversores, electrónica de potencia).
    capex_energy : float
        CAPEX de energía en €/kWh (celdas de batería).
    opex_fixed : float
        OPEX fijo anual en €/kW/año.
    opex_variable : float
        OPEX variable en €/MWh descargado.
    efficiency : float
        Eficiencia de ida y vuelta (round-trip efficiency) como decimal (0-1).
    degradation_rate : float
        Tasa de degradación anual de capacidad como decimal (0-1).
    lifetime_years : int
        Vida útil del proyecto en años.
    discount_rate : float
        Tasa de descuento anual como decimal (0-1).
    cycles_per_day : float
        Número de ciclos de carga/descarga por día.
    availability : float
        Factor de disponibilidad del sistema como decimal (0-1).
    """

    power_capacity_mw: float
    energy_capacity_mwh: float
    capex_power: float  # €/kW
    capex_energy: float  # €/kWh
    opex_fixed: float  # €/kW/año
    opex_variable: float  # €/MWh
    efficiency: float  # 0-1
    degradation_rate: float  # 0-1 anual
    lifetime_years: int
    discount_rate: float  # 0-1
    cycles_per_day: float = 1.0
    availability: float = 0.95


@dataclass
class LCOEResult:
    """Resultados del cálculo de LCOE.

    Attributes
    ----------
    lcoe : float
        Coste nivelado de energía en €/MWh.
    total_capex : float
        CAPEX total del proyecto en €.
    npv_opex : float
        Valor presente neto del OPEX en €.
    total_cost : float
        Coste total del ciclo de vida en €.
    total_energy_mwh : float
        Energía total descargada durante la vida útil en MWh.
    npv_energy_mwh : float
        Valor presente neto de la energía descargada en MWh.
    annual_energy_mwh : float
        Energía descargada anualmente (primer año) en MWh.
    payback_years : Optional[float]
        Período de retorno de la inversión en años.
    annual_revenue_potential : float
        Potencial de ingresos anuales basado en spreads en €.
    npv_profit : float
        Valor presente neto del beneficio en €.
    """

    lcoe: float
    total_capex: float
    npv_opex: float
    total_cost: float
    total_energy_mwh: float
    npv_energy_mwh: float
    annual_energy_mwh: float
    payback_years: Optional[float]
    annual_revenue_potential: float
    npv_profit: float


def calculate_capex(params: BESSParameters) -> float:
    """Calcula el CAPEX total del sistema BESS.

    Parameters
    ----------
    params : BESSParameters
        Parámetros del sistema BESS.

    Returns
    -------
    float
        CAPEX total en €.
    """
    # Convertir MW a kW para el cálculo
    power_kw = params.power_capacity_mw * 1000
    energy_kwh = params.energy_capacity_mwh * 1000

    capex_power_total = power_kw * params.capex_power
    capex_energy_total = energy_kwh * params.capex_energy

    return capex_power_total + capex_energy_total


def calculate_annual_energy_throughput(
    params: BESSParameters, year: int = 1
) -> float:
    """Calcula la energía descargada anualmente considerando degradación.

    Parameters
    ----------
    params : BESSParameters
        Parámetros del sistema BESS.
    year : int, optional
        Año del proyecto (1 = primer año). Por defecto 1.

    Returns
    -------
    float
        Energía descargada en MWh para el año especificado.
    """
    # Capacidad efectiva considerando degradación
    degradation_factor = (1 - params.degradation_rate) ** (year - 1)
    effective_capacity = params.energy_capacity_mwh * degradation_factor

    # Energía descargada = capacidad × ciclos/día × días × eficiencia × disponibilidad
    days_per_year = 365
    annual_energy = (
        effective_capacity
        * params.cycles_per_day
        * days_per_year
        * params.efficiency
        * params.availability
    )

    return annual_energy


def calculate_annual_opex(params: BESSParameters, year: int = 1) -> float:
    """Calcula el OPEX anual del sistema BESS.

    Parameters
    ----------
    params : BESSParameters
        Parámetros del sistema BESS.
    year : int, optional
        Año del proyecto. Por defecto 1.

    Returns
    -------
    float
        OPEX anual en €.
    """
    power_kw = params.power_capacity_mw * 1000

    # OPEX fijo basado en potencia
    opex_fixed_total = power_kw * params.opex_fixed

    # OPEX variable basado en energía descargada
    annual_energy = calculate_annual_energy_throughput(params, year)
    opex_variable_total = annual_energy * params.opex_variable

    return opex_fixed_total + opex_variable_total


def calculate_lcoe(
    params: BESSParameters, avg_spread: float = 0.0
) -> LCOEResult:
    """Calcula el LCOE del sistema BESS.

    El LCOE se calcula como:
    LCOE = (CAPEX + NPV(OPEX)) / NPV(Energía descargada)

    Parameters
    ----------
    params : BESSParameters
        Parámetros del sistema BESS.
    avg_spread : float, optional
        Spread medio esperado en €/MWh para calcular ingresos potenciales.
        Por defecto 0.0.

    Returns
    -------
    LCOEResult
        Resultados del cálculo de LCOE.
    """
    # Calcular CAPEX total
    total_capex = calculate_capex(params)

    # Calcular NPV de OPEX y energía
    npv_opex = 0.0
    npv_energy = 0.0
    total_energy = 0.0
    npv_revenue = 0.0

    for year in range(1, params.lifetime_years + 1):
        # Factor de descuento para este año
        discount_factor = 1 / ((1 + params.discount_rate) ** year)

        # OPEX de este año
        annual_opex = calculate_annual_opex(params, year)
        npv_opex += annual_opex * discount_factor

        # Energía de este año
        annual_energy = calculate_annual_energy_throughput(params, year)
        npv_energy += annual_energy * discount_factor
        total_energy += annual_energy

        # Ingresos potenciales de este año
        annual_revenue = annual_energy * avg_spread
        npv_revenue += annual_revenue * discount_factor

    # Calcular LCOE
    total_cost = total_capex + npv_opex
    lcoe = total_cost / npv_energy if npv_energy > 0 else float("inf")

    # Calcular energía del primer año para referencia
    annual_energy_year1 = calculate_annual_energy_throughput(params, 1)

    # Calcular período de retorno
    if avg_spread > 0:
        annual_margin = annual_energy_year1 * (avg_spread - lcoe)
        if annual_margin > 0:
            # Simplificación: retorno sin considerar degradación ni descuento
            payback_years = total_capex / annual_margin
        else:
            payback_years = None
    else:
        payback_years = None

    # Calcular NPV del beneficio
    npv_profit = npv_revenue - total_cost

    # Ingresos potenciales del primer año
    annual_revenue_potential = annual_energy_year1 * avg_spread

    return LCOEResult(
        lcoe=lcoe,
        total_capex=total_capex,
        npv_opex=npv_opex,
        total_cost=total_cost,
        total_energy_mwh=total_energy,
        npv_energy_mwh=npv_energy,
        annual_energy_mwh=annual_energy_year1,
        payback_years=payback_years,
        annual_revenue_potential=annual_revenue_potential,
        npv_profit=npv_profit,
    )


def calculate_lcoe_sensitivity(
    params: BESSParameters,
    variable: str,
    values: list,
    avg_spread: float = 0.0,
) -> pd.DataFrame:
    """Realiza análisis de sensibilidad del LCOE variando un parámetro.

    Parameters
    ----------
    params : BESSParameters
        Parámetros base del sistema BESS.
    variable : str
        Nombre del parámetro a variar.
    values : list
        Lista de valores a probar para el parámetro.
    avg_spread : float, optional
        Spread medio para calcular rentabilidad. Por defecto 0.0.

    Returns
    -------
    pd.DataFrame
        DataFrame con resultados de sensibilidad.
    """
    results = []

    for value in values:
        # Crear copia de parámetros con valor modificado
        params_dict = {
            "power_capacity_mw": params.power_capacity_mw,
            "energy_capacity_mwh": params.energy_capacity_mwh,
            "capex_power": params.capex_power,
            "capex_energy": params.capex_energy,
            "opex_fixed": params.opex_fixed,
            "opex_variable": params.opex_variable,
            "efficiency": params.efficiency,
            "degradation_rate": params.degradation_rate,
            "lifetime_years": params.lifetime_years,
            "discount_rate": params.discount_rate,
            "cycles_per_day": params.cycles_per_day,
            "availability": params.availability,
        }

        if variable in params_dict:
            params_dict[variable] = value
        else:
            raise ValueError(f"Parámetro desconocido: {variable}")

        test_params = BESSParameters(**params_dict)
        result = calculate_lcoe(test_params, avg_spread)

        results.append(
            {
                "variable": variable,
                "value": value,
                "lcoe": result.lcoe,
                "npv_profit": result.npv_profit,
                "payback_years": result.payback_years,
            }
        )

    return pd.DataFrame(results)


def create_lcoe_breakdown_chart(result: LCOEResult) -> go.Figure:
    """Crea un gráfico de desglose de costes del LCOE.

    Parameters
    ----------
    result : LCOEResult
        Resultados del cálculo de LCOE.

    Returns
    -------
    plotly.graph_objects.Figure
        Gráfico de barras apiladas con desglose de costes.
    """
    # Calcular componentes del LCOE
    capex_component = result.total_capex / result.npv_energy_mwh
    opex_component = result.npv_opex / result.npv_energy_mwh

    fig = go.Figure(
        data=[
            go.Bar(
                name="CAPEX",
                x=["LCOE"],
                y=[capex_component],
                marker_color="#2E86AB",
                text=[f"{capex_component:.2f}"],
                textposition="inside",
            ),
            go.Bar(
                name="OPEX",
                x=["LCOE"],
                y=[opex_component],
                marker_color="#A23B72",
                text=[f"{opex_component:.2f}"],
                textposition="inside",
            ),
        ]
    )

    fig.update_layout(
        barmode="stack",
        title="Desglose del LCOE por Componente",
        yaxis_title="€/MWh",
        template="plotly_white",
        font=dict(family="Calibri"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_profitability_chart(
    result: LCOEResult, avg_spread: float
) -> go.Figure:
    """Crea un gráfico comparativo de LCOE vs Spread.

    Parameters
    ----------
    result : LCOEResult
        Resultados del cálculo de LCOE.
    avg_spread : float
        Spread medio en €/MWh.

    Returns
    -------
    plotly.graph_objects.Figure
        Gráfico de barras comparando LCOE y spread.
    """
    margin = avg_spread - result.lcoe
    color_margin = "#28A745" if margin > 0 else "#DC3545"

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="LCOE (Coste)",
            x=["Análisis"],
            y=[result.lcoe],
            marker_color="#DC3545",
            text=[f"{result.lcoe:.2f}"],
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Spread (Ingreso)",
            x=["Análisis"],
            y=[avg_spread],
            marker_color="#28A745",
            text=[f"{avg_spread:.2f}"],
            textposition="outside",
        )
    )

    fig.update_layout(
        barmode="group",
        title=f"LCOE vs Spread Medio (Margen: {margin:.2f} €/MWh)",
        yaxis_title="€/MWh",
        template="plotly_white",
        font=dict(family="Calibri"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_sensitivity_chart(
    sensitivity_df: pd.DataFrame, variable_label: str
) -> go.Figure:
    """Crea un gráfico de análisis de sensibilidad.

    Parameters
    ----------
    sensitivity_df : pd.DataFrame
        DataFrame con resultados de sensibilidad.
    variable_label : str
        Etiqueta descriptiva del parámetro variado.

    Returns
    -------
    plotly.graph_objects.Figure
        Gráfico de línea mostrando sensibilidad del LCOE.
    """
    fig = px.line(
        sensitivity_df,
        x="value",
        y="lcoe",
        title=f"Sensibilidad del LCOE a {variable_label}",
        labels={"value": variable_label, "lcoe": "LCOE (€/MWh)"},
        markers=True,
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Calibri"),
    )

    return fig


def create_cashflow_chart(
    params: BESSParameters, avg_spread: float
) -> go.Figure:
    """Crea un gráfico de flujo de caja acumulado del proyecto.

    Parameters
    ----------
    params : BESSParameters
        Parámetros del sistema BESS.
    avg_spread : float
        Spread medio en €/MWh.

    Returns
    -------
    plotly.graph_objects.Figure
        Gráfico de flujo de caja acumulado.
    """
    # Calcular CAPEX inicial
    total_capex = calculate_capex(params)

    # Calcular flujos de caja anuales
    years = list(range(params.lifetime_years + 1))
    cashflows = [-total_capex]  # Año 0: inversión inicial
    cumulative = [-total_capex]

    for year in range(1, params.lifetime_years + 1):
        annual_energy = calculate_annual_energy_throughput(params, year)
        annual_revenue = annual_energy * avg_spread
        annual_opex = calculate_annual_opex(params, year)
        annual_cashflow = annual_revenue - annual_opex

        cashflows.append(annual_cashflow)
        cumulative.append(cumulative[-1] + annual_cashflow)

    df = pd.DataFrame(
        {
            "Año": years,
            "Flujo de Caja": cashflows,
            "Flujo Acumulado": cumulative,
        }
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Flujo Anual",
            x=df["Año"],
            y=df["Flujo de Caja"],
            marker_color=[
                "#28A745" if x >= 0 else "#DC3545" for x in df["Flujo de Caja"]
            ],
        )
    )

    fig.add_trace(
        go.Scatter(
            name="Flujo Acumulado",
            x=df["Año"],
            y=df["Flujo Acumulado"],
            mode="lines+markers",
            line=dict(color="#2E86AB", width=3),
            marker=dict(size=8),
        )
    )

    # Añadir línea de referencia en y=0
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title="Flujo de Caja del Proyecto BESS",
        xaxis_title="Año",
        yaxis_title="€",
        template="plotly_white",
        font=dict(family="Calibri"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig
