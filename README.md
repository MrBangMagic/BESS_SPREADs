# BESS_SPREADs

Herramienta para calcular spreads de precios eléctricos con datos de la API de ESIOS.

## Token de autenticación

Este proyecto necesita un token de la API de ESIOS para funcionar.

### Variables de entorno

El token debe estar disponible en la variable de entorno `TOKEN`.

Para desarrollo local:

1. Copia `.env.example` a `.env` y añade tu token:

   ```bash
   cp .env.example .env
   echo "TOKEN=mi_token" >> .env
   ```

2. Carga la variable en tu sesión:

   ```bash
   export $(grep -v '^#' .env | xargs)
   ```

   También puedes usar herramientas como `python-dotenv`, `dotenv-cli` o `direnv` para cargar las variables automáticamente.

### Producción

En entornos de producción define la variable `TOKEN` mediante los mecanismos del sistema operativo o usando un gestor de secretos (por ejemplo, AWS Secrets Manager, Google Secret Manager o Docker secrets). Nunca incluyas el token directamente en el repositorio.
