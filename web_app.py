from datetime import date, datetime
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from SPREADS import compute_spreads, fetch_esios_data
from lcoe import (
    BESSParameters,
    calculate_lcoe,
    create_lcoe_breakdown_chart,
    create_profitability_chart,
    create_cashflow_chart,
)

st.set_page_config(
    page_title="BESSpread",
    layout="wide",
    page_icon=str(Path(__file__).parent / "images" / "logo.png"),
)

st.markdown(
    """
    <style>
    * {font-family: 'Calibri', sans-serif;}
    .stApp {
        background: linear-gradient(135deg, #D4EDDA, #C3E6CB);
        color: #333333;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #39e5ff;
        text-shadow: 0 0 10px #39e5ff;
    }
    .stButton>button {
        background: linear-gradient(135deg, #8EC6C5, #A9E5D0);
        color: #000000;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton>button:hover {
        box-shadow: 0 0 12px #00ffcc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.image(Path(__file__).parent / "images" / "logo.png", width=200)
st.title("BESSpread")
st.write(
    "BESSpread es una herramienta que calcula el spread diario y el spread medio mensual. "
    "Los datos se obtienen en tiempo real desde la API de ESIOS (https://api.esios.ree.es/indicators/600). "
    "Permite descargar los resultados en formato Excel."
)
st.markdown(
    "[Cómo usar la aplicación](#como-usar-la-aplicacion)", unsafe_allow_html=True
)

st.markdown("""### Cómo usar la aplicación
1. Selecciona el rango de fechas que deseas analizar.
2. Selecciona el intervalo de análisis (15 minutos u horario).
3. Introduce el número de horas de almacenamiento.
4. Pulsa **Calcular** para obtener los datos de la API y generar los resultados.
""")

with st.form("spread_form"):
    col1, col2, col3, col4 = st.columns(4)
    start_date = col1.date_input(
        "Fecha de inicio",
        value=date.today(),
        help="Fecha inicial del análisis (AAAA-MM-DD)",
    )
    end_date = col2.date_input(
        "Fecha de fin",
        value=date.today(),
        help="Fecha final del análisis (AAAA-MM-DD)",
    )
    intervalo = col3.selectbox(
        "Intervalo",
        options=["Horario", "15 minutos"],
        index=0,
        help="Selecciona el intervalo de análisis",
    )
    horas = col4.number_input(
        "Horas",
        min_value=1,
        max_value=24,
        value=6,
        help="Horas de almacenamiento (1-24)",
    )

    errors = False
    if start_date > end_date:
        st.error("La fecha inicial debe ser anterior o igual a la final.")
        errors = True
    if not (1 <= horas <= 24):
        st.error("Las horas deben estar entre 1 y 24.")
        errors = True

    submitted = st.form_submit_button("Calcular", disabled=errors)

if submitted:
    try:
        with st.spinner("Obteniendo datos de la API de ESIOS y calculando spreads..."):
            # Obtener datos desde la API con el intervalo seleccionado
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.min.time())

            # Usar "fifteen_minutes" solo para 15 minutos, None para horario (evitar "hour" que genera problemas)
            time_trunc = "fifteen_minutes" if intervalo == "15 minutos" else None
            data = fetch_esios_data(start_datetime, end_datetime, time_trunc=time_trunc)

            # Calcular spreads con los datos obtenidos
            (
                daily_stats,
                monthly_stats,
                fig_daily,
                fig_monthly,
            ) = compute_spreads(
                start_datetime,
                end_datetime,
                int(horas),
                data,  # Pasar los datos ya obtenidos
                intervalo=intervalo,  # Pasar el intervalo seleccionado
            )

        col_img1, col_text1 = st.columns([1, 8])
        col_img1.image(Path(__file__).parent / "images" / "b.png", width=40)
        col_text1.subheader("Spread diario")
        st.plotly_chart(fig_daily, use_container_width=True)

        col_img2, col_text2 = st.columns([1, 8])
        col_img2.image(Path(__file__).parent / "images" / "c.png", width=40)
        col_text2.subheader("Spread mensual")
        st.plotly_chart(fig_monthly, use_container_width=True)

        st.subheader("Precio medio y volatilidad")
        metrics_cols = st.columns(len(monthly_stats["geo_name"].unique()))
        for col, geo in zip(metrics_cols, monthly_stats["geo_name"].unique()):
            data_geo = monthly_stats[monthly_stats["geo_name"] == geo]
            avg_price = data_geo["price_avg"].mean()
            vol = data_geo["volatility"].mean()
            col.metric(f"{geo} precio medio", f"{avg_price:.2f} €/MWh")
            col.metric(f"{geo} volatilidad", f"{vol:.2f} €/MWh")
        st.caption(
            "Precio medio: media simple de los precios horarios filtrados por día/mes. "
            "Volatilidad: desviación estándar de los precios horarios como indicador de riesgo.",
        )

        daily_buffer = io.BytesIO()
        with pd.ExcelWriter(daily_buffer, engine="openpyxl") as writer:
            daily_stats.to_excel(writer, index=False)
        daily_buffer.seek(0)

        monthly_buffer = io.BytesIO()
        with pd.ExcelWriter(monthly_buffer, engine="openpyxl") as writer:
            monthly_stats.to_excel(writer, index=False)
        monthly_buffer.seek(0)

        # Crear buffer para datos de entrada (horarios o 15 minutos)
        data_buffer = io.BytesIO()
        with pd.ExcelWriter(data_buffer, engine="openpyxl") as writer:
            data.to_excel(writer, index=False)
        data_buffer.seek(0)

        # Nombre de archivo según intervalo
        data_filename = "datos_15min.xlsx" if intervalo == "15 minutos" else "datos_horarios.xlsx"
        btn_label = f"Descargar Datos {intervalo}"

        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            st.download_button(
                btn_label,
                data=data_buffer,
                file_name=data_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        with col_btn2:
            st.download_button(
                "Descargar Spread Diario",
                data=daily_buffer,
                file_name="spread_diario.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        with col_btn3:
            st.download_button(
                "Descargar Spread Mensual",
                data=monthly_buffer,
                file_name="spread_mensual.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # Calcular spread medio de España para LCOE
        spain_data = monthly_stats[monthly_stats["geo_name"] == "España"]
        if not spain_data.empty:
            avg_spread_spain = spain_data["spread"].mean()
        else:
            avg_spread_spain = monthly_stats["spread"].mean()

        # Guardar datos en session_state para LCOE
        st.session_state["avg_spread"] = avg_spread_spain
        st.session_state["spread_calculated"] = True

    except Exception as exc:
        st.error(f"Ocurrió un error: {exc}")

# Sección LCOE
st.markdown("---")
st.header("Análisis LCOE (Coste Nivelado de Energía)")
st.write(
    "El LCOE permite evaluar si el sistema BESS es rentable comparando el coste "
    "de almacenamiento con los ingresos potenciales por arbitraje (spreads)."
)

with st.expander("ℹ️ ¿Qué es el LCOE?", expanded=False):
    st.markdown("""
    **LCOE (Levelized Cost of Energy)** es el coste medio por MWh de energía
    descargada durante toda la vida útil del sistema.

    **Fórmula:**
    ```
    LCOE = (CAPEX + NPV(OPEX)) / NPV(Energía descargada)
    ```

    **Interpretación:**
    - Si LCOE < Spread medio → El proyecto es **rentable**
    - Si LCOE > Spread medio → El proyecto **no es rentable**

    **Componentes del coste:**
    - **CAPEX Potencia**: Inversores, electrónica de potencia (€/kW)
    - **CAPEX Energía**: Celdas de batería (€/kWh)
    - **OPEX Fijo**: Mantenimiento, seguros, personal (€/kW/año)
    - **OPEX Variable**: Costes por energía descargada (€/MWh)
    """)

with st.form("lcoe_form"):
    st.subheader("Parámetros del Sistema BESS")

    col_sys1, col_sys2 = st.columns(2)
    power_mw = col_sys1.number_input(
        "Potencia (MW)",
        min_value=0.1,
        max_value=1000.0,
        value=10.0,
        step=1.0,
        help="Capacidad de potencia del sistema en MW",
    )
    energy_mwh = col_sys2.number_input(
        "Energía (MWh)",
        min_value=0.1,
        max_value=10000.0,
        value=40.0,
        step=1.0,
        help="Capacidad de energía del sistema en MWh",
    )

    st.subheader("Costes de Inversión (CAPEX)")
    col_capex1, col_capex2 = st.columns(2)
    capex_power = col_capex1.number_input(
        "CAPEX Potencia (€/kW)",
        min_value=0.0,
        max_value=1000.0,
        value=150.0,
        step=10.0,
        help="Coste de inversores y electrónica de potencia",
    )
    capex_energy = col_capex2.number_input(
        "CAPEX Energía (€/kWh)",
        min_value=0.0,
        max_value=1000.0,
        value=250.0,
        step=10.0,
        help="Coste de las celdas de batería",
    )

    st.subheader("Costes Operativos (OPEX)")
    col_opex1, col_opex2 = st.columns(2)
    opex_fixed = col_opex1.number_input(
        "OPEX Fijo (€/kW/año)",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=1.0,
        help="Mantenimiento, seguros, personal",
    )
    opex_variable = col_opex2.number_input(
        "OPEX Variable (€/MWh)",
        min_value=0.0,
        max_value=50.0,
        value=2.0,
        step=0.5,
        help="Costes proporcionales a la energía descargada",
    )

    st.subheader("Parámetros Técnicos")
    col_tech1, col_tech2, col_tech3 = st.columns(3)
    efficiency = col_tech1.number_input(
        "Eficiencia Round-Trip (%)",
        min_value=50.0,
        max_value=100.0,
        value=88.0,
        step=1.0,
        help="Eficiencia de carga y descarga combinada",
    )
    degradation = col_tech2.number_input(
        "Degradación Anual (%)",
        min_value=0.0,
        max_value=10.0,
        value=2.0,
        step=0.1,
        help="Pérdida de capacidad por año",
    )
    cycles_day = col_tech3.number_input(
        "Ciclos por Día",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        help="Número de ciclos completos de carga/descarga por día",
    )

    st.subheader("Parámetros Financieros")
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    lifetime = col_fin1.number_input(
        "Vida Útil (años)",
        min_value=1,
        max_value=30,
        value=15,
        step=1,
        help="Duración del proyecto",
    )
    discount_rate = col_fin2.number_input(
        "Tasa de Descuento (%)",
        min_value=0.0,
        max_value=20.0,
        value=7.0,
        step=0.5,
        help="Tasa de descuento anual (WACC)",
    )
    availability = col_fin3.number_input(
        "Disponibilidad (%)",
        min_value=50.0,
        max_value=100.0,
        value=95.0,
        step=1.0,
        help="Porcentaje de tiempo operativo",
    )

    # Spread manual o calculado
    st.subheader("Spread para Análisis de Rentabilidad")
    use_calculated_spread = st.checkbox(
        "Usar spread calculado del análisis anterior",
        value=st.session_state.get("spread_calculated", False),
        help="Si está marcado, usa el spread medio calculado anteriormente",
    )

    if use_calculated_spread and st.session_state.get("spread_calculated"):
        spread_value = st.session_state.get("avg_spread", 20.0)
        st.info(f"Spread medio calculado: {spread_value:.2f} €/MWh")
    else:
        spread_value = st.number_input(
            "Spread Medio (€/MWh)",
            min_value=0.0,
            max_value=200.0,
            value=20.0,
            step=1.0,
            help="Diferencia media entre precio de venta y compra",
        )

    lcoe_submitted = st.form_submit_button("Calcular LCOE")

if lcoe_submitted:
    # Crear parámetros BESS
    bess_params = BESSParameters(
        power_capacity_mw=power_mw,
        energy_capacity_mwh=energy_mwh,
        capex_power=capex_power,
        capex_energy=capex_energy,
        opex_fixed=opex_fixed,
        opex_variable=opex_variable,
        efficiency=efficiency / 100,
        degradation_rate=degradation / 100,
        lifetime_years=lifetime,
        discount_rate=discount_rate / 100,
        cycles_per_day=cycles_day,
        availability=availability / 100,
    )

    # Calcular LCOE
    lcoe_result = calculate_lcoe(bess_params, spread_value)

    # Mostrar resultados principales
    st.subheader("Resultados del LCOE")

    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    col_res1.metric(
        "LCOE",
        f"{lcoe_result.lcoe:.2f} €/MWh",
        delta=None,
    )
    col_res2.metric(
        "Spread Medio",
        f"{spread_value:.2f} €/MWh",
    )

    margin = spread_value - lcoe_result.lcoe
    margin_color = "normal" if margin >= 0 else "inverse"
    col_res3.metric(
        "Margen",
        f"{margin:.2f} €/MWh",
        delta=f"{'Rentable' if margin > 0 else 'No rentable'}",
        delta_color=margin_color,
    )

    if lcoe_result.payback_years is not None and lcoe_result.payback_years > 0:
        payback_str = f"{lcoe_result.payback_years:.1f} años"
    else:
        payback_str = "N/A"
    col_res4.metric("Payback", payback_str)

    # Métricas detalladas
    st.subheader("Desglose de Costes e Ingresos")
    col_det1, col_det2, col_det3 = st.columns(3)

    col_det1.metric(
        "CAPEX Total",
        f"{lcoe_result.total_capex:,.0f} €".replace(",", "."),
    )
    col_det2.metric(
        "NPV OPEX",
        f"{lcoe_result.npv_opex:,.0f} €".replace(",", "."),
    )
    col_det3.metric(
        "Coste Total Ciclo de Vida",
        f"{lcoe_result.total_cost:,.0f} €".replace(",", "."),
    )

    col_det4, col_det5, col_det6 = st.columns(3)
    col_det4.metric(
        "Energía Anual (Año 1)",
        f"{lcoe_result.annual_energy_mwh:,.0f} MWh".replace(",", "."),
    )
    col_det5.metric(
        "Energía Total Vida Útil",
        f"{lcoe_result.total_energy_mwh:,.0f} MWh".replace(",", "."),
    )
    col_det6.metric(
        "NPV Beneficio",
        f"{lcoe_result.npv_profit:,.0f} €".replace(",", "."),
        delta="Positivo" if lcoe_result.npv_profit > 0 else "Negativo",
        delta_color="normal" if lcoe_result.npv_profit > 0 else "inverse",
    )

    # Gráficos
    st.subheader("Visualización")

    tab1, tab2, tab3 = st.tabs(
        ["Desglose LCOE", "LCOE vs Spread", "Flujo de Caja"]
    )

    with tab1:
        fig_breakdown = create_lcoe_breakdown_chart(lcoe_result)
        st.plotly_chart(fig_breakdown, use_container_width=True)

    with tab2:
        fig_profit = create_profitability_chart(lcoe_result, spread_value)
        st.plotly_chart(fig_profit, use_container_width=True)

    with tab3:
        fig_cashflow = create_cashflow_chart(bess_params, spread_value)
        st.plotly_chart(fig_cashflow, use_container_width=True)

    # Resumen de rentabilidad
    st.subheader("Conclusión")
    if margin > 0:
        st.success(
            f"✅ **El proyecto es RENTABLE**. El margen de {margin:.2f} €/MWh "
            f"genera un NPV de {lcoe_result.npv_profit:,.0f} € durante "
            f"{lifetime} años.".replace(",", ".")
        )
    else:
        st.error(
            f"❌ **El proyecto NO es rentable** con los parámetros actuales. "
            f"El LCOE ({lcoe_result.lcoe:.2f} €/MWh) supera el spread medio "
            f"({spread_value:.2f} €/MWh)."
        )
