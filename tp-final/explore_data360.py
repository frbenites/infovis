"""
Exploración de la API Data360 del Banco Mundial.

Endpoints (base: https://data360api.worldbank.org):
- POST /data360/searchv2     -> búsqueda vectorial sobre el índice de metadata
- GET  /data360/indicators   -> indicadores de UNA base (requiere datasetId)
- GET  /data360/data         -> observaciones de un indicador
- POST /data360/metadata     -> metadata por filtro
- GET  /data360/disaggregation

Spec: https://raw.githubusercontent.com/worldbank/open-api-specs/refs/heads/main/Data360%20Open_API.json

Genera bajo tp-final/data/:
- databases_facet.json     (respuesta cruda del facet por database_id)
- databases.json           (lista derivada [{id, indicator_count}])
- databases_named.json     (mapa id -> nombre humano)
- indicators_sample.json   (indicadores de 3 bases representativas)
- data_sample.json         (observaciones de un indicador concreto)
"""

import json
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

BASE = "https://data360api.worldbank.org"
UA = "Mozilla/5.0 (compatible; infovis-tp-final/1.0)"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def post(path: str, body: dict) -> dict:
    req = Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA, "Accept": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(path: str, params: dict | None = None) -> dict:
    url = BASE + path
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def dump(name: str, obj) -> Path:
    p = DATA_DIR / name
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    return p


def step_databases_facet() -> list[dict]:
    body = {
        "search": "*",
        "top": 0,
        "count": True,
        "filter": "type eq 'indicator'",
        "facets": ["series_description/database_id,count:1000"],
    }
    resp = post("/data360/searchv2", body)
    dump("databases_facet.json", resp)
    facets = resp["@search.facets"]["series_description/database_id"]
    indicator_total = resp["@odata.count"]
    facet_sum = sum(f["count"] for f in facets)
    print(f"[bases]  distintas = {len(facets)}")
    print(f"[bases]  indicadores totales = {indicator_total}")
    print(f"[bases]  suma de facet counts = {facet_sum}  (debe igualar al total)")
    assert facet_sum == indicator_total, "facet truncado: subir count:N"
    derived = [{"id": f["value"], "indicator_count": f["count"]} for f in facets]
    dump("databases.json", derived)
    return derived


def step_database_names(databases: list[dict]) -> dict[str, str]:
    body = {
        "search": "*",
        "top": 1000,
        "filter": "type eq 'indicator'",
        "select": "series_description/database_id,series_description/database_name",
    }
    id_to_name: dict[str, str] = {}
    skip = 0
    while len(id_to_name) < len(databases):
        body["skip"] = skip
        resp = post("/data360/searchv2", body)
        rows = resp.get("value", [])
        if not rows:
            break
        for row in rows:
            sd = row.get("series_description") or {}
            db_id = sd.get("database_id")
            db_name = sd.get("database_name")
            if db_id and db_name and db_id not in id_to_name:
                id_to_name[db_id] = db_name
        skip += len(rows)
        if skip >= 10000:
            break
    dump("databases_named.json", id_to_name)
    missing = [d["id"] for d in databases if d["id"] not in id_to_name]
    print(f"[nombres] resueltos = {len(id_to_name)}/{len(databases)}; faltan = {len(missing)}")
    if missing:
        print(f"[nombres] sin nombre: {missing[:10]}")
    return id_to_name


def step_indicators_sample(sample_ids: list[str]) -> dict:
    out: dict = {}
    for db_id in sample_ids:
        try:
            resp = get("/data360/indicators", {"datasetId": db_id})
        except Exception as e:
            print(f"[indicators] {db_id}: ERROR {e}")
            continue
        items = resp if isinstance(resp, list) else resp.get("value", resp)
        n = len(items) if hasattr(items, "__len__") else None
        print(f"[indicators] {db_id}: {n} entradas")
        out[db_id] = items
    dump("indicators_sample.json", out)
    return out


def step_data_sample(database_id: str, indicator_id: str) -> dict:
    params = {
        "DATABASE_ID": database_id,
        "INDICATOR": indicator_id,
        "REF_AREA": "ARG",
        "timePeriodFrom": "2015",
        "timePeriodTo": "2022",
    }
    try:
        resp = get("/data360/data", params)
    except Exception as e:
        print(f"[data] ERROR {e}")
        return {}
    dump("data_sample.json", resp)
    rows = resp if isinstance(resp, list) else resp.get("value", [])
    print(f"[data] {database_id}/{indicator_id} ARG 2015-2022: {len(rows)} observaciones")
    if rows:
        keys = sorted(rows[0].keys()) if isinstance(rows[0], dict) else []
        print(f"[data] dimensiones del primer registro: {keys}")
    return resp


def step_topics_overview() -> Counter:
    body = {
        "search": "*",
        "top": 0,
        "count": True,
        "filter": "type eq 'indicator'",
        "facets": ["series_description/topics/name,count:50"],
    }
    resp = post("/data360/searchv2", body)
    facets = resp["@search.facets"].get("series_description/topics/name", [])
    print(f"[topics] top temáticas (de {len(facets)} mostradas):")
    for f in facets[:15]:
        print(f"         {f['count']:5}  {f['value']}")
    return Counter({f["value"]: f["count"] for f in facets})


def main() -> None:
    print("=== Punto 1: Exploración API Data360 ===\n")

    databases = step_databases_facet()

    print()
    names = step_database_names(databases)

    print("\n[top-10 bases por cantidad de indicadores]")
    for d in databases[:10]:
        name = names.get(d["id"], "(sin nombre)")
        print(f"  {d['indicator_count']:5}  {d['id']:25} {name}")

    print()
    step_indicators_sample(["WB_WDI", "IMF_BOP", "WB_FINDEX"])

    print()
    step_topics_overview()

    print()
    step_data_sample("WB_WDI", "WB_WDI_NY_GDP_MKTP_CD")

    print("\n=== Fin ===")
    print(f"Archivos generados en {DATA_DIR}")


if __name__ == "__main__":
    main()
