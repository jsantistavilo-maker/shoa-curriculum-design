from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from statistics import mode
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

import networkx as nx

BASE_DIR = Path(__file__).resolve().parent
PROGRAMAS_PATH = BASE_DIR / "programas_estructurados.json"
CURRICULUM_PATH = BASE_DIR / "curriculum_data.json"
OUTPUT_PATH = BASE_DIR / "progresion_analisis.json"

TOPICO_A_NIVEL = {
    "F1": 1,
    "F2": 1,
    "F3": 1,
    "H1": 2,
    "H2": 2,
    "H3": 2,
    "H4": 3,
    "H5": 3,
    "H6": 4,
    "H7": 4,
    "H8": 5,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_code(raw: str) -> str:
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def inferir_semestre_desde_codigo(codigo: str) -> int:
    m = re.search(r"(\d{3})", codigo)
    if not m:
        return 1
    valor = int(m.group(1))
    return max(1, min(6, valor // 100))


def extraer_codigos_en_texto(texto: str, codigos_validos: list[str]) -> list[str]:
    normal = normalize_code(texto)
    encontrados: list[str] = []
    for codigo in codigos_validos:
        if normalize_code(codigo) in normal:
            encontrados.append(codigo)
    return encontrados


def mapear_topicos_por_asignatura(curriculum: dict[str, Any], codigos: list[str]) -> dict[str, dict[str, Any]]:
    hojas = curriculum.get("leaves", [])
    salida: dict[str, dict[str, Any]] = {c: {"topicos": [], "nivel": None} for c in codigos}

    for codigo in codigos:
        pesos: dict[str, float] = {}
        for leaf in hojas:
            asgn = str(leaf.get("asgn_shoa") or "")
            if normalize_code(codigo) in normalize_code(asgn):
                topico = str(leaf.get("topico") or "").strip()
                peso = float(leaf.get("shoa") or 0.0)
                if topico:
                    pesos[topico] = pesos.get(topico, 0.0) + peso
        topicos_ordenados = sorted(pesos.items(), key=lambda x: x[1], reverse=True)
        topicos = [t for t, _ in topicos_ordenados]
        if topicos:
            dominante = topicos[0]
            salida[codigo] = {
                "topicos": topicos,
                "nivel": TOPICO_A_NIVEL.get(dominante, 2),
            }
    return salida


def main() -> None:
    if not PROGRAMAS_PATH.exists():
        raise FileNotFoundError(
            "No existe programas_estructurados.json. Ejecuta primero extractor_programas.py"
        )
    if not CURRICULUM_PATH.exists():
        raise FileNotFoundError("No existe curriculum_data.json en la carpeta del proyecto.")

    programas_data = load_json(PROGRAMAS_PATH)
    curriculum_data = load_json(CURRICULUM_PATH)
    programas = programas_data.get("programas", [])

    asignaturas = [
        p for p in programas if p.get("codigo_asignatura") and not p.get("error")
    ]
    codigos = [p["codigo_asignatura"] for p in asignaturas]
    topicos_por_asig = mapear_topicos_por_asignatura(curriculum_data, codigos)

    grafo = nx.DiGraph()
    resumen_asignaturas: dict[str, dict[str, Any]] = {}

    for p in asignaturas:
        codigo = p["codigo_asignatura"]
        nivel = topicos_por_asig.get(codigo, {}).get("nivel")
        if nivel is None:
            nivel = 2
        semestre = p.get("semestre") or inferir_semestre_desde_codigo(codigo)
        nombre = p.get("nombre_asignatura") or codigo
        prerreq = p.get("prerrequisitos") or []

        grafo.add_node(
            codigo,
            nombre=nombre,
            semestre=semestre,
            nivel_iho=nivel,
            topicos=topicos_por_asig.get(codigo, {}).get("topicos", []),
        )

        resumen_asignaturas[codigo] = {
            "codigo": codigo,
            "nombre": nombre,
            "semestre_actual": semestre,
            "nivel_iho_predominante": nivel,
            "topicos_iho": topicos_por_asig.get(codigo, {}).get("topicos", []),
            "prerrequisitos": [],
        }

        for pre in prerreq:
            if pre in codigos and pre != codigo:
                grafo.add_edge(pre, codigo)
                resumen_asignaturas[codigo]["prerrequisitos"].append(pre)

    problemas: list[dict[str, Any]] = []
    aristas_con_problema: list[dict[str, str]] = []

    for pre, curso in grafo.edges():
        sem_pre = grafo.nodes[pre]["semestre"]
        sem_cur = grafo.nodes[curso]["semestre"]
        if sem_pre > sem_cur:
            descripcion = (
                f"La asignatura {curso} (semestre {sem_cur}) depende de {pre} "
                f"(semestre {sem_pre}), por lo que la base aparece después."
            )
            problemas.append(
                {
                    "tipo": "prerrequisito_fuera_de_secuencia",
                    "asignatura": curso,
                    "asignatura_base": pre,
                    "semestre_asignatura": sem_cur,
                    "semestre_base": sem_pre,
                    "descripcion": descripcion,
                }
            )
            aristas_con_problema.append({"desde": pre, "hacia": curso})

    semestres_por_nivel: dict[int, list[int]] = {}
    for n in grafo.nodes:
        nivel = int(grafo.nodes[n]["nivel_iho"])
        sem = int(grafo.nodes[n]["semestre"])
        semestres_por_nivel.setdefault(nivel, []).append(sem)

    semestre_referencia_nivel: dict[int, int] = {}
    for nivel, sems in semestres_por_nivel.items():
        try:
            semestre_referencia_nivel[nivel] = mode(sems)
        except Exception:
            semestre_referencia_nivel[nivel] = min(sems)

    for codigo in grafo.nodes:
        nivel = int(grafo.nodes[codigo]["nivel_iho"])
        sem = int(grafo.nodes[codigo]["semestre"])
        if nivel >= 4:
            base_lvl = 2
            sem_base = semestre_referencia_nivel.get(base_lvl, sem)
            if sem_base > sem:
                descripcion = (
                    f"La asignatura {codigo} (semestre {sem}) enseña tópicos de nivel {nivel} "
                    f"antes de consolidar contenidos base de nivel {base_lvl} (semestre {sem_base})."
                )
                problemas.append(
                    {
                        "tipo": "progresion_por_nivel",
                        "asignatura": codigo,
                        "semestre_asignatura": sem,
                        "nivel_asignatura": nivel,
                        "nivel_base": base_lvl,
                        "semestre_base": sem_base,
                        "descripcion": descripcion,
                    }
                )

    sin_prerrequisitos_claros: list[dict[str, Any]] = []
    for codigo in grafo.nodes:
        nivel = int(grafo.nodes[codigo]["nivel_iho"])
        if nivel >= 3 and grafo.in_degree(codigo) == 0:
            sin_prerrequisitos_claros.append(
                {
                    "codigo": codigo,
                    "nombre": grafo.nodes[codigo]["nombre"],
                    "nivel_iho_predominante": nivel,
                    "descripcion": (
                        "Asignatura de nivel avanzado sin prerrequisitos explícitos; "
                        "debería revisarse la dependencia con fundamentos previos."
                    ),
                }
            )

    salida = {
        "resumen": {
            "total_asignaturas": grafo.number_of_nodes(),
            "total_dependencias": grafo.number_of_edges(),
            "total_problemas": len(problemas),
            "total_sin_prerrequisitos_claros": len(sin_prerrequisitos_claros),
        },
        "asignaturas": list(resumen_asignaturas.values()),
        "dependencias": [{"desde": u, "hacia": v} for u, v in grafo.edges()],
        "aristas_con_problema": aristas_con_problema,
        "problemas_progresion": problemas,
        "asignaturas_sin_prerrequisitos_claros": sin_prerrequisitos_claros,
    }

    OUTPUT_PATH.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ Análisis de progresión generado en: {OUTPUT_PATH}")
    print(f"📌 Problemas detectados: {len(problemas)}")


if __name__ == "__main__":
    main()
