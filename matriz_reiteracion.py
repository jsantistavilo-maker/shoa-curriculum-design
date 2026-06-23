from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from thefuzz import fuzz

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
PROGRAMAS_PATH = BASE_DIR / "programas_estructurados.json"
PROGRESION_PATH = BASE_DIR / "progresion_analisis.json"
OUTPUT_PATH = BASE_DIR / "reiteracion_matriz.json"

FUZZY_THRESHOLD = 75
DEDUP_INTRA_THRESHOLD = 90


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_key(texto: str) -> str:
    """Normaliza un texto para usar como clave de deduplicación."""
    import re as _re
    import unicodedata as _ud
    t = _ud.normalize("NFKD", texto)
    t = "".join(ch for ch in t if not _ud.combining(ch))
    t = t.lower().strip()
    t = _re.sub(r"[.,:;!?]+$", "", t)
    t = _re.sub(r"\s+", " ", t).strip()
    return t


def _dedup_contenidos_intra(contenidos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Elimina contenidos near-duplicados dentro de la misma asignatura.

    Si dos items del mismo código tienen similitud >= DEDUP_INTRA_THRESHOLD,
    conserva el de texto más largo.
    """
    from collections import defaultdict

    por_codigo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in contenidos:
        por_codigo[c["codigo"]].append(c)

    resultado: list[dict[str, Any]] = []
    eliminados = 0
    for codigo, items in por_codigo.items():
        keep = [True] * len(items)
        for i in range(len(items)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(items)):
                if not keep[j]:
                    continue
                sim = fuzz.token_set_ratio(items[i]["contenido"], items[j]["contenido"])
                if sim >= DEDUP_INTRA_THRESHOLD:
                    shorter = j if len(items[j]["contenido"]) <= len(items[i]["contenido"]) else i
                    keep[shorter] = False
                    eliminados += 1
        resultado.extend(items[k] for k in range(len(items)) if keep[k])

    if eliminados:
        print(f"  Contenidos intra-asignatura deduplicados: {eliminados} eliminados")
    return resultado


def clasificar_reiteracion(
    similitud: int,
    nivel_1: int,
    nivel_2: int,
    sem_1: int,
    sem_2: int,
    texto_1: str,
    texto_2: str,
) -> str:
    texto = f"{texto_1} {texto_2}".lower()
    tiene_profundizacion = any(
        kw in texto
        for kw in [
            "avanz",
            "aplic",
            "proyecto",
            "integr",
            "analisis",
            "procesamiento",
        ]
    )
    if similitud >= 90 and abs(nivel_1 - nivel_2) <= 1 and abs(sem_1 - sem_2) <= 1:
        return "INNECESARIA"
    if (nivel_2 > nivel_1 or sem_2 > sem_1) and tiene_profundizacion:
        return "JUSTIFICADA"
    return "REVISAR"


def estimar_horas_duplicadas(horas_1: int, horas_2: int, tipo: str) -> float:
    base = min(horas_1 or 0, horas_2 or 0)
    if tipo == "INNECESARIA":
        return round(base * 0.6, 2)
    if tipo == "REVISAR":
        return round(base * 0.25, 2)
    return 0.0


def main() -> None:
    if not PROGRAMAS_PATH.exists():
        raise FileNotFoundError(
            "No existe programas_estructurados.json. Ejecuta primero extractor_programas.py"
        )
    if not PROGRESION_PATH.exists():
        raise FileNotFoundError(
            "No existe progresion_analisis.json. Ejecuta primero analisis_progresion.py"
        )

    programas_data = load_json(PROGRAMAS_PATH).get("programas", [])
    progresion_data = load_json(PROGRESION_PATH)
    meta_asig = {a["codigo"]: a for a in progresion_data.get("asignaturas", [])}

    contenidos_raw: list[dict[str, Any]] = []
    for prog in programas_data:
        codigo = prog.get("codigo_asignatura")
        if not codigo or prog.get("error"):
            continue
        unidades = prog.get("unidades_tematicas", [])
        semestre = int(meta_asig.get(codigo, {}).get("semestre_actual", 1))
        nivel = int(meta_asig.get(codigo, {}).get("nivel_iho_predominante", 2))
        for unidad in unidades:
            u_horas = int(unidad.get("horas_asignadas", 0))
            for c in unidad.get("contenidos_especificos", []):
                t = str(c).strip()
                if len(t) >= 12:
                    contenidos_raw.append(
                        {
                            "codigo": codigo,
                            "semestre": semestre,
                            "nivel": nivel,
                            "unidad": unidad.get("nombre_unidad", ""),
                            "horas_unidad": u_horas,
                            "contenido": t,
                        }
                    )

    print(f"  Contenidos extraídos: {len(contenidos_raw)}")
    contenidos = _dedup_contenidos_intra(contenidos_raw)
    print(f"  Contenidos tras dedup intra-asignatura: {len(contenidos)}")

    reiteraciones: list[dict[str, Any]] = []
    pares_vistos: set[frozenset] = set()
    total_bruto = 0

    for i in range(len(contenidos)):
        for j in range(i + 1, len(contenidos)):
            c1 = contenidos[i]
            c2 = contenidos[j]
            if c1["codigo"] == c2["codigo"]:
                continue
            similitud = fuzz.token_set_ratio(c1["contenido"], c2["contenido"])
            if similitud < FUZZY_THRESHOLD:
                continue

            total_bruto += 1

            par_key: frozenset = frozenset([
                (c1["codigo"], _norm_key(c1["contenido"])),
                (c2["codigo"], _norm_key(c2["contenido"])),
            ])
            if par_key in pares_vistos:
                continue
            pares_vistos.add(par_key)

            tipo = clasificar_reiteracion(
                similitud=similitud,
                nivel_1=c1["nivel"],
                nivel_2=c2["nivel"],
                sem_1=c1["semestre"],
                sem_2=c2["semestre"],
                texto_1=c1["contenido"],
                texto_2=c2["contenido"],
            )
            horas_dup = estimar_horas_duplicadas(
                c1["horas_unidad"],
                c2["horas_unidad"],
                tipo,
            )

            reiteraciones.append(
                {
                    "contenido": c1["contenido"],
                    "contenido_relacionado": c2["contenido"],
                    "asignatura_1": c1["codigo"],
                    "semestre_1": c1["semestre"],
                    "nivel_iho_1": c1["nivel"],
                    "asignatura_2": c2["codigo"],
                    "semestre_2": c2["semestre"],
                    "nivel_iho_2": c2["nivel"],
                    "tipo_reiteracion": tipo,
                    "similitud": similitud,
                    "horas_duplicadas_estimadas": horas_dup,
                }
            )

    print(f"  Reiteraciones antes (bruto): {total_bruto} pares")
    print(f"  Reiteraciones tras frozenset: {len(reiteraciones)} pares únicos")

    # ── Dedup inter-par: por cada par (asig1, asig2), colapsar entradas
    #    donde el contenido target (c2) es el mismo o muy similar,
    #    conservando solo la de mayor similitud.
    pre_inter = len(reiteraciones)
    from collections import defaultdict as _dlist

    por_par: dict[tuple[str, str], list[dict]] = _dlist(list)
    for r in reiteraciones:
        par = tuple(sorted([r["asignatura_1"], r["asignatura_2"]]))
        por_par[par].append(r)

    reiteraciones_final: list[dict[str, Any]] = []
    for par, entries in por_par.items():
        entries.sort(key=lambda e: -e["similitud"])
        keep = [True] * len(entries)
        for i in range(len(entries)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(entries)):
                if not keep[j]:
                    continue
                sim_c2 = fuzz.token_set_ratio(
                    entries[i]["contenido_relacionado"],
                    entries[j]["contenido_relacionado"],
                )
                sim_c1 = fuzz.token_set_ratio(
                    entries[i]["contenido"],
                    entries[j]["contenido"],
                )
                if sim_c2 >= 85 or sim_c1 >= 85:
                    keep[j] = False
        reiteraciones_final.extend(entries[k] for k in range(len(entries)) if keep[k])

    reiteraciones = reiteraciones_final
    print(f"  Reiteraciones únicas después: {len(reiteraciones)} pares")

    reiteraciones.sort(
        key=lambda r: (
            {"INNECESARIA": 0, "REVISAR": 1, "JUSTIFICADA": 2}.get(
                r["tipo_reiteracion"], 9
            ),
            -r["similitud"],
        )
    )

    asignaturas = sorted({c["codigo"] for c in contenidos})
    idx = {a: i for i, a in enumerate(asignaturas)}
    matriz = [[0 for _ in asignaturas] for _ in asignaturas]
    matriz_innecesaria = [[0 for _ in asignaturas] for _ in asignaturas]

    for r in reiteraciones:
        i = idx[r["asignatura_1"]]
        j = idx[r["asignatura_2"]]
        matriz[i][j] += 1
        matriz[j][i] += 1
        if r["tipo_reiteracion"] == "INNECESARIA":
            matriz_innecesaria[i][j] += 1
            matriz_innecesaria[j][i] += 1

    horas_recuperables = round(
        sum(
            r["horas_duplicadas_estimadas"]
            for r in reiteraciones
            if r["tipo_reiteracion"] == "INNECESARIA"
        ),
        2,
    )

    salida = {
        "resumen": {
            "total_reiteraciones_detectadas": len(reiteraciones),
            "total_innecesarias": sum(
                1 for r in reiteraciones if r["tipo_reiteracion"] == "INNECESARIA"
            ),
            "horas_recuperables_estimadas": horas_recuperables,
            "threshold_fuzzy": FUZZY_THRESHOLD,
        },
        "reiteraciones": reiteraciones,
        "heatmap": {
            "asignaturas": asignaturas,
            "matriz_total": matriz,
            "matriz_innecesaria": matriz_innecesaria,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ Matriz de reiteración generada en: {OUTPUT_PATH}")
    print(f"♻️ Horas recuperables estimadas: {horas_recuperables}")


if __name__ == "__main__":
    main()
