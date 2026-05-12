# TP Final — Punto 1: Exploración de la API Data360

## API 

**URL Base de la API:** `https://data360api.worldbank.org`
**Specs:** [`worldbank/open-api-specs · Data360 Open_API.json`](https://raw.githubusercontent.com/worldbank/open-api-specs/refs/heads/main/Data360%20Open_API.json)

Endpoints disponibles:

| Método | Path | Propósito |
|---|---|---|
| `POST` | `/data360/searchv2` | Búsqueda vectorial sobre el índice de metadata. Permite filtrar y facetar. |
| `GET`  | `/data360/indicators` | Lista de indicadores de una base (requiere `datasetId`). |
| `GET`  | `/data360/data` | Observaciones de un indicador (filtros: `DATABASE_ID`, `INDICATOR`, `REF_AREA`, `TIME_PERIOD`, `timePeriodFrom/To`, `SEX`, `AGE`, `URBANISATION`, `skip`). |
| `POST` | `/data360/metadata` | Metadata por query (filter/select). |
| `GET`  | `/data360/disaggregation` | Desagregaciones disponibles para un indicador. |


## Bases de datos

**Total: 161 bases de datos.**

El catálogo no expone un endpoint que devuelva "todas las bases de datos". Sí expone, en cambio, un índice de **indicadores**, y cada indicador tiene un campo que dice de qué base proviene (`series_description.database_id`). Entonces, para contar las bases pedimos al servidor que agrupe los indicadores por ese campo y nos diga, para cada valor distinto, cuántos indicadores hay. La cantidad de grupos resultantes = cantidad de bases distintas.

El request es:

```http
POST /data360/searchv2
{
  "search": "*", "top": 0, "count": true,
  "filter": "type eq 'indicator'",
  "facets": ["series_description/database_id,count:1000"]
}
```

Validación:

- 161 buckets distintos -> 161 bases de datos.
- Suma de counts = **10.211** = total de documentos indicator → no hay truncamiento.
- 0 nulls, 0 duplicados case-insensitive, todos los ids con formato `ORG_DATASET` legítimo.

**Corolario:** este conteo cubre las bases que tienen al menos un indicador en el índice. 

### Distribución por organismo

56 de las 161 bases provienen del Banco Mundial (`WB_*`), seguido por IMF (29), FAO (13) y OECD (7). El resto se reparte entre ~40 organismos más: WEF, ITU, UNCTAD, WRI, UNESCO, WHO, ILO, UNICEF, UNEP, WIPO, V-Dem, Freedom House, Reporters Without Borders, Ookla, etc.

| Organismo | # bases |
|---|---:|
| World Bank (WB) | 56 |
| IMF | 29 |
| FAO | 13 |
| OECD | 7 |
| WEF, ITU, UNCTAD, WRI | 3 c/u |
| BS, FH, GEM, IFC, UN | 2 c/u |
| Otros (32 organismos) | 1 c/u |

### Top-10 bases por cantidad de indicadores

| # indicadores | id | nombre |
|---:|---|---|
| 1533 | `WB_WDI`      | World Development Indicators (WDI) |
| 1146 | `IMF_BOP`     | Balance of Payments (BOP) and International Investment Position (IIP) |
| 1072 | `WB_EDSTATS`  | Education Statistics |
|  593 | `IMF_FSI`     | Financial Soundness Indicators (FSIs) |
|  582 | `WB_ES`       | Enterprise Surveys |
|  495 | `IMF_IFS`     | International Financial Statistics (IFS) |
|  363 | `WB_GS`       | Gender Statistics |
|  280 | `WB_FINDEX`   | Global Findex Database |
|  193 | `BS_SGI`      | Sustainable Governance Indicators (SGI) |
|  192 | `WB_HNP`      | Health Nutrition and Population Statistics |

22 bases tienen un único indicador.


## Indicadores

**Total: 10.211 indicadores** distribuidos entre las 161 bases.

Los códigos de indicador por lo que vimos siempre llevan el prefijo de la base. Por ejemplo, en `WB_WDI`:

- `WB_WDI_NY_GDP_MKTP_CD` — GDP (current US$)
- `WB_WDI_IC_FRM_INFM_ZS` — Firms that do not report all sales for tax purposes (% of firms)

Para listar los indicadores de una base: `GET /data360/indicators?datasetId=WB_WDI`. (Ojo: este endpoint devuelve series desagregadas, no sólo conceptos — en `WB_WDI` retorna 1533 entradas que coincide con el facet, pero en `IMF_BOP` retorna 5209 entradas frente a 1146 del facet, porque expande variantes.)

### Top-15 temáticas (campo `topics`)

| # indicadores | tema |
|---:|---|
| 5570 | Prosperity |
| 2471 | Economic Policy |
| 1610 | Finance |
| 1561 | Macro-financial Policies |
| 1201 | Financial Stability and Integrity |
| 1026 | Trade, Investment and Competitiveness |
|  881 | People |
|  843 | Institutions |
|  686 | Fiscal Policy |
|  630 | Investment and Business Climate |
|  428 | Gender |
|  385 | Financial Inclusion, Infrastructure and Access |
|  366 | Economic and Sociopolitical Governance |
|  362 | Public Institutions |
|  313 | Education |

(Un mismo indicador puede tener varios `topics`, así que la suma de la columna excede 10.211.)

## Estructura de los datos

Cada observación devuelta por `GET /data360/data` es un objeto plano con estas dimensiones:

| Campo | Significado |
|---|---|
| `DATABASE_ID` | Base de origen (ej. `WB_WDI`). |
| `INDICATOR` | Código de indicador. |
| `REF_AREA` | País/región (ISO-3, ej. `ARG`, o agregados como `AFE`). |
| `TIME_PERIOD` | Período (año, "2022"). |
| `FREQ` | Frecuencia (`A` = anual). |
| `OBS_VALUE` | Valor de la observación. |
| `UNIT_MEASURE`, `UNIT_MULT`, `UNIT_TYPE` | Unidad y escala (ej. `USD`). |
| `SEX`, `AGE`, `URBANISATION` | Desagregaciones demográficas (`_T` = total). |
| `COMP_BREAKDOWN_1/2/3` | Desagregaciones compuestas (`_Z` = no aplica). |
| `OBS_STATUS`, `OBS_CONF` | Calidad/confidencialidad (`A` = normal, `PU` = público). |
| `DECIMALS`, `TIME_FORMAT`, `LATEST_DATA`, `COMMENT_OBS`, `COMMENT_TS` | Metadata accesoria. |

Ejemplo real — GDP de Argentina en 2009 desde `WB_WDI`:

```json
{
  "DATABASE_ID": "WB_WDI",
  "INDICATOR": "WB_WDI_NY_GDP_MKTP_CD",
  "REF_AREA": "ARG",
  "TIME_PERIOD": "2009",
  "OBS_VALUE": "332976484577.6189",
  "UNIT_MEASURE": "USD",
  "FREQ": "A",
  "SEX": "_T", "AGE": "_T", "URBANISATION": "_T"
}
```

**Paginación:** las respuestas se cortan en 1000 filas; se itera con `skip`.

**Cobertura:** país-año es la granularidad típica, con cobertura mundial (todos los ISO-3) y series que arrancan típicamente entre 1960 y 2000 según el indicador.
