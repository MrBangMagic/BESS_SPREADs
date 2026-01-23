"""Script de diagnóstico para el error de conversión de datetime_600"""
import pandas as pd
from datetime import datetime
from SPREADS import fetch_esios_data, compute_spreads

print("=" * 60)
print("Test 1: Petición corta (menos de 7 días)")
print("=" * 60)
try:
    df_short = fetch_esios_data(datetime(2024, 1, 1), datetime(2024, 1, 5))
    print(f"✓ Datos obtenidos: {len(df_short)} filas")
    print(f"  Columnas: {df_short.columns.tolist()}")
    print(f"  Tipos: {df_short.dtypes.to_dict()}")
    print(f"  Primer datetime_600: {repr(df_short['datetime_600'].iloc[0])}")
    print(f"  Tipo del primer valor: {type(df_short['datetime_600'].iloc[0])}")

    # Probar conversión
    df_short["datetime"] = pd.to_datetime(df_short["datetime_600"], errors="coerce")
    print(f"  Después de to_datetime: {df_short['datetime'].dtype}")
    print(f"  ¿Es datetime? {pd.api.types.is_datetime64_any_dtype(df_short['datetime'])}")
    print(f"  Valores NaT: {df_short['datetime'].isna().sum()}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("Test 2: Petición larga (más de 7 días - un mes)")
print("=" * 60)
try:
    df_long = fetch_esios_data(datetime(2024, 1, 1), datetime(2024, 1, 31))
    print(f"✓ Datos obtenidos: {len(df_long)} filas")
    print(f"  Columnas: {df_long.columns.tolist()}")
    print(f"  Tipos: {df_long.dtypes.to_dict()}")
    print(f"  Primer datetime_600: {repr(df_long['datetime_600'].iloc[0])}")
    print(f"  Tipo del primer valor: {type(df_long['datetime_600'].iloc[0])}")
    print(f"  Último datetime_600: {repr(df_long['datetime_600'].iloc[-1])}")

    # Probar conversión
    df_long["datetime_test"] = pd.to_datetime(df_long["datetime_600"], errors="coerce")
    print(f"  Después de to_datetime: {df_long['datetime_test'].dtype}")
    print(f"  ¿Es datetime? {pd.api.types.is_datetime64_any_dtype(df_long['datetime_test'])}")
    print(f"  Valores NaT: {df_long['datetime_test'].isna().sum()}")

    # Verificar si hay valores únicos problemáticos
    if df_long['datetime_test'].isna().any():
        print("\n  Valores problemáticos en datetime_600:")
        problematic = df_long[df_long['datetime_test'].isna()]['datetime_600'].unique()
        for val in problematic[:10]:  # Mostrar los primeros 10
            print(f"    - {repr(val)} (tipo: {type(val)})")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test 3: Probar compute_spreads con rango largo")
print("=" * 60)
try:
    daily, monthly, fig_d, fig_m = compute_spreads(
        datetime(2024, 1, 1),
        datetime(2024, 1, 31),
        horas=4,
        intervalo="Horario"
    )
    print("✓ compute_spreads exitoso")
    print(f"  Datos diarios: {len(daily)} filas")
    print(f"  Datos mensuales: {len(monthly)} filas")
except Exception as e:
    print(f"✗ Error en compute_spreads: {e}")
    import traceback
    traceback.print_exc()
