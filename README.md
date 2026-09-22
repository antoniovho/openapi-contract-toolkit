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

Copia `tools/openapi_contracts/` al proyecto y añade:

```toml
[project.scripts]
contract-sync = "tools.openapi_contracts.cli:contract_sync_main"
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

uv run generate-source --rest-server --api api-rest
uv run generate-source --rest-client --api catalog-client
```

`contract-sync` descarga primero a un temporal, comprueba SHA-256 y solo entonces sustituye el fichero destino.

`generate-source` vuelve a verificar el SHA-256 local antes de generar. No descarga implícitamente: sincronización y generación son responsabilidades separadas.

## OpenAPI Generator

Por defecto se invoca:

```bash
openapi-generator-cli
```

Puedes adaptar la instalación a cada proyecto o CI. También puedes indicar otro comando:

```bash
OPENAPI_GENERATOR_CMD="npx --yes @openapitools/openapi-generator-cli" uv run generate-source --rest-server --api api-rest
```

Conviene fijar la versión del generador en CI.

## Releases privadas

`contract-sync` usa `GITHUB_TOKEN` si está definido.

## Portabilidad

Para aplicar esto a otro proyecto:
1. Copia `tools/openapi_contracts/`.
2. Copia/adapta las secciones de `example/pyproject.fragment.toml`.
3. Configura los contratos y generadores propios.
4. Ejecuta `uv run contract-sync`.
