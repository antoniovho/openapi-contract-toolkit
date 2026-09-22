# OpenAPI Contract Toolkit

Toolkit portable para proyectos Python + uv que consumen uno o varios contratos OpenAPI publicados como assets inmutables de GitHub Releases.

## Diseño

La configuración reproducible vive en `pyproject.toml`. `.env` queda para secretos/configuración de máquina.

Cada contrato declara:
- `version`
- `repository`
- `tag` y `artifact` parametrizables con `{version}`
- `sha256`
- `output`

Cada generador `server` o `client` referencia un contrato por nombre, evitando duplicar paths/versiones.

## Instalación

El toolkit fija Python `3.12.12` y uv `0.10.6` en `.tool-versions`. Con ambos
plugins disponibles en `asdf`, prepara el entorno local con:

```bash
asdf install
uv venv --python 3.12.12 .venv
```

Ejecuta las pruebas usando el entorno creado:

```bash
.venv/bin/python -m unittest tests/test_config.py
```

El paquete instala los tres comandos directamente. Si prefieres copiar `tools/openapi_contracts/` al proyecto consumidor, añade la dependencia y los scripts:

```toml
[project]
dependencies = [
	"tomlkit>=0.13,<1.0",
]

[project.scripts]
contract-sync = "tools.openapi_contracts.cli:contract_sync_main"
contract-update = "tools.openapi_contracts.cli:contract_update_main"
generate-source = "tools.openapi_contracts.cli:generate_source_main"
```

Requiere Python 3.11+ y no añade dependencias Python externas.

## Ejemplo

```toml
[tool.openapi-contracts.contracts.test-service]
version = "0.1.1"
repository = "antoniovho/app-devtools"
tag = "test-service-api-v{version}"
artifact = "test-service-api-{version}.yml"
sha256 = "ac7d05caca3ad57a88be8892561c83f980ec81dbcc3db33748af45aa818c286c"
output = "contracts/test-service-api.yml"

[tool.openapi-contracts.contracts.catalog-service]
version = "1.4.2"
repository = "my-org/contracts"
tag = "catalog-service-api-v{version}"
artifact = "catalog-service-api-{version}.yml"
sha256 = "REPLACE_WITH_SHA256"
output = "contracts/catalog-service-api.yml"

[tool.openapi-contracts.generators.rest.server.api-rest]
contract = "test-service"
generator = "python-fastapi"
output = "generated/server"
package-name = "test_service_api"

[tool.openapi-contracts.generators.rest.client.catalog-client]
contract = "catalog-service"
generator = "python"
output = "generated/clients/catalog_service"
package-name = "catalog_service_client"
```

## Comandos

```bash
uv run contract-sync
uv run contract-sync test-service
uv run contract-sync test-service --dry-run

uv run contract-update test-service --version 0.1.2
uv run contract-update test-service --version 0.1.2 --dry-run

uv run generate-source --rest-server --api api-rest
uv run generate-source --rest-client --api catalog-client
```

`contract-sync` descarga primero a un temporal, comprueba SHA-256 y solo entonces sustituye el fichero destino.

`contract-update` actualiza deliberadamente una dependencia: requiere una versión explícita, descarga el artifact de esa release, calcula su SHA-256 y cambia únicamente `version` y `sha256` del contrato seleccionado. Conserva el formato y los comentarios no relacionados de `pyproject.toml`; si la descarga falla, no modifica la configuración. El artifact local se reemplaza únicamente tras haber sido validado.

`generate-source` vuelve a verificar el SHA-256 local antes de generar. No descarga implícitamente: sincronización y generación son responsabilidades separadas.

En resumen:

- `contract-update` cambia la versión que consume el proyecto.
- `contract-sync` reproduce exactamente la versión ya fijada en Git.
- `generate-source` genera código usando el contrato local verificado.

## OpenAPI Generator

Fija el wrapper y la versión del motor en el `pyproject.toml` consumidor para no
requerir exports manuales:

```toml
[tool.openapi-contracts]
generator-command = "npx --yes @openapitools/openapi-generator-cli@2.41.0"
generator-version = "7.10.0"
```

Con esa configuración, basta ejecutar:

```bash
uv run generate-source --rest-server --api api-rest
```

`OPENAPI_GENERATOR_CMD` y `OPENAPI_GENERATOR_VERSION` siguen permitidos solo
como overrides temporales para diagnóstico o CI.

## Releases privadas

`contract-sync` usa `GITHUB_TOKEN` si está definido.

## Portabilidad

Para aplicar esto a otro proyecto:
1. Instala el paquete `openapi-contract-toolkit` o copia `tools/openapi_contracts/`.
2. Copia/adapta las secciones de `example/pyproject.fragment.toml` si has elegido copiar el código.
3. Configura los contratos y generadores propios.
4. Ejecuta `uv run contract-sync`.
