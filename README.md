# BESSpread

BESSpread es una herramienta que calcula el spread diario y el spread medio mensual basándose en datos de precios de energía obtenidos desde la API de ESIOS (Red Eléctrica de España).

## Requisitos previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación y ejecución local

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd BESS_SPREADs
```

### 2. Crear un entorno virtual (recomendado)

```bash
# En Linux/Mac
python3 -m venv venv
source venv/bin/activate

# En Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

Las dependencias incluyen:
- pandas: procesamiento de datos
- plotly: visualización de gráficos
- streamlit: framework de aplicación web
- openpyxl: exportación a Excel
- requests: llamadas a la API de ESIOS

### 4. Ejecutar la aplicación

```bash
streamlit run web_app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## Uso de la aplicación

1. **Selecciona el rango de fechas**: Elige las fechas de inicio y fin para el análisis
2. **Selecciona el intervalo**: Elige entre análisis horario o de 15 minutos
3. **Introduce las horas de almacenamiento**: Valor entre 1 y 24 horas
4. **Pulsa Calcular**: La aplicación obtendrá los datos de ESIOS y calculará los spreads
5. **Descarga los resultados**: Puedes descargar los datos en formato Excel

## Características

- Obtención de datos en tiempo real desde la API de ESIOS
- Cálculo de spreads diarios y mensuales
- Análisis con intervalos horarios o de 15 minutos
- Visualización de gráficos interactivos
- Cálculo de precio medio y volatilidad
- Exportación de resultados a Excel

## Estructura del proyecto

- `web_app.py`: Aplicación principal de Streamlit
- `SPREADS.py`: Lógica de cálculo de spreads
- `requirements.txt`: Dependencias del proyecto
- `images/`: Recursos gráficos
- `styles/`: Estilos CSS

## Problemas comunes

### Error de conexión a la API

Si obtienes errores de conexión a la API de ESIOS, verifica:
- Tu conexión a internet
- Que la API de ESIOS esté disponible en https://api.esios.ree.es

### Error de importación

Si obtienes errores de módulos no encontrados:
```bash
pip install -r requirements.txt --force-reinstall
```

## Contribuir

Para contribuir al proyecto, crea una rama con el prefijo `claude/` y el ID de sesión correspondiente.
