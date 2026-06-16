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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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

    contenidos: list[dict[str, Any]] = []
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
                    contenidos.append(
                        {
                            "codigo": codigo,
                            "semestre": semestre,
                            "nivel": nivel,
                            "unidad": unidad.get("nombre_unidad", ""),
                            "horas_unidad": u_horas,
                            "contenido": t,
                        }
                    )

    reiteraciones: list[dict[str, Any]] = []
    for i in range(len(contenidos)):
        for j in range(i + 1, len(contenidos)):
            c1 = contenidos[i]
            c2 = contenidos[j]
            if c1["codigo"] == c2["codigo"]:
                continue
            similitud = fuzz.token_set_ratio(c1["contenido"], c2["contenido"])
            if similitud < FUZZY_THRESHOLD:
                continue

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
