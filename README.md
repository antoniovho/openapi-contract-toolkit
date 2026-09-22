# OpenAPI Contract Toolkit

Toolkit para proyectos Python con `uv` que consumen contratos OpenAPI publicados
como assets inmutables de GitHub Releases. Descarga cada contrato con su
checksum, y genera de forma reproducible código de servidor o cliente.

La configuración vive en el `pyproject.toml` del proyecto consumidor. Los
contratos descargados y el código generado deben poder recrearse, por lo que no
se editan manualmente.

## Requisitos

- Python >= 3.12
- `uv`
- Node.js >= 22
- `npm`/`npx` cuando se use el wrapper de OpenAPI Generator.
- Un contrato publicado como asset de una GitHub Release y su SHA-256.

Para una Release privada, configura `GITHUB_TOKEN` en el entorno antes de
sincronizar el contrato.

## Instalar En Un Proyecto Consumidor

Añade el wheel de una Release concreta al grupo que uses para desarrollo o
generación. La URL contiene una versión inmutable; después `uv lock` registra
el hash del wheel en `uv.lock`.

```toml
[project.optional-dependencies]
dev = [
  "openapi-contract-toolkit @ https://github.com/antoniovho/openapi-contract-toolkit/releases/download/v0.1.0/openapi_contract_toolkit-0.1.0-py3-none-any.whl",
]
```

Después actualiza e instala el entorno:

```bash
uv lock
uv sync --extra dev --locked
```

El paquete proporciona estos comandos:

```text
contract-sync
contract-update
generate-source
```

## Configurar Contratos Y Generadores

Añade esta configuración al `pyproject.toml` consumidor. Un contrato indica
qué asset de Release descargar; cada generador referencia uno de esos contratos.

```toml
[tool.openapi-contracts]
generator-command = "npx --yes @openapitools/openapi-generator-cli@2.41.0"

[tool.openapi-contracts.contracts.test-service]
version = "0.1.1"
repository = "antoniovho/app-devtools"
tag = "test-service-api-v{version}"
artifact = "test-service-api-{version}.yml"
sha256 = "ac7d05caca3ad57a88be8892561c83f980ec81dbcc3db33748af45aa818c286c"
output = "contracts/open_api/test-service-api.yml"

[tool.openapi-contracts.contracts.catalog-service]
version = "1.4.2"
repository = "my-org/contracts"
tag = "catalog-service-api-v{version}"
artifact = "catalog-service-api-{version}.yml"
sha256 = "REPLACE_WITH_RELEASE_SHA256"
output = "contracts/open_api/catalog-service-api.yml"

[tool.openapi-contracts.generators.rest.server.test-service-server]
contract = "test-service"
generator = "python-fastapi"
output = "generated/test_service_server"
package-name = "test_service_server"
sourceFolder = ""

[tool.openapi-contracts.generators.rest.client.catalog-client]
contract = "catalog-service"
generator = "python"
output = "generated/catalog_client"
package-name = "catalog_client"
sourceFolder = ""
```

`repository`, `tag` y `artifact` forman la URL de descarga. Para el contrato
`test-service` anterior, el toolkit descarga:

```text
https://github.com/antoniovho/app-devtools/releases/download/test-service-api-v0.1.1/test-service-api-0.1.1.yml
```

`output` es una ruta relativa al directorio que contiene el `pyproject.toml`.
Los generadores pueden crear un proyecto completo en esa ruta, incluyendo su
propio `pyproject.toml`, pruebas y ficheros de contenedor. Por ello, usa un
directorio aislado dentro de `generated/`. `package-name` identifica el paquete
Python dentro de ese proyecto. Las propiedades no reservadas, como
`sourceFolder`, se reenvían a OpenAPI Generator; `sourceFolder = ""` evita una
carpeta fuente adicional.

## Generar Un Servidor

Primero descarga y verifica el contrato fijado. Después genera el servidor:

```bash
uv run contract-sync test-service
uv run generate-source --rest-server --api test-service-server
```

El argumento de `--api` es el último componente de la sección TOML:
`[tool.openapi-contracts.generators.rest.server.test-service-server]`.

El generador vuelve a comprobar el SHA-256 del contrato local. No descarga
implícitamente para que sincronización y generación puedan revisarse por
separado.

## Generar Un Cliente

Un cliente sigue el mismo flujo, pero selecciona el rol `client` y su nombre:

```bash
uv run contract-sync catalog-service
uv run generate-source --rest-client --api catalog-client
```

Puedes configurar varios servidores y clientes para el mismo contrato, cada
uno con su propio nombre, generador, paquete y directorio de salida.

## Actualizar Un Contrato

Actualizar una dependencia es explícito. El comando descarga el asset de la
versión solicitada, calcula su SHA-256, actualiza únicamente `version` y
`sha256` en el `pyproject.toml`, y sustituye el contrato local solo si la
descarga es válida:

```bash
uv run contract-update test-service --version 0.1.2
uv run generate-source --rest-server --api test-service-server
```

Revisa y confirma el cambio en `pyproject.toml` antes de incorporarlo. Para
ensayar los comandos sin cambiar archivos:

```bash
uv run contract-sync test-service --dry-run
uv run contract-update test-service --version 0.1.2 --dry-run
uv run generate-source --rest-server --api test-service-server --dry-run
```

## Versiones Del Generador

`generator-command` fija el wrapper de Node. Cuando se utiliza
`@openapitools/openapi-generator-cli`, fija la versión del motor Java en el
archivo `openapitools.json` del proyecto consumidor:

```json
{
  "generator-cli": {
    "version": "7.25.0"
  }
}
```

Mantén ese archivo en control de versiones. Es la única fuente de verdad para
la versión del motor; no declares también `generator-version` en
`pyproject.toml`. `OPENAPI_GENERATOR_CMD` sigue disponible como override
temporal para diagnóstico o CI.

## Desarrollo Del Toolkit

El repositorio fija Python `3.12.12` y `uv 0.10.6` en `.tool-versions`. Con
`asdf` configurado:

```bash
asdf install
uv sync --locked
uv run python -m unittest discover -s tests -v
```

Cada Release publica un wheel, un sdist y `SHA256SUMS`. Los proyectos
consumidores deben fijar una URL de wheel de Release concreta, actualizar el
lockfile y revisar el cambio de versión deliberadamente.
