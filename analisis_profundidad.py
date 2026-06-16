from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR        = Path(__file__).resolve().parent
PROGRAMAS_PATH  = BASE_DIR / "programas_estructurados.json"
CURRICULUM_PATH = BASE_DIR / "curriculum_data.json"
NIVELES_IHO_PATH = BASE_DIR / "niveles_iho_norma.json"
OUTPUT_PATH     = BASE_DIR / "profundidad_iho.json"

# Escala unificada IHO S-5A: B=Basic < I=Intermediate < A=Advanced
NIVEL_ORD: dict[str, int] = {"B": 1, "I": 2, "A": 3}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_code(raw: str) -> str:
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def cargar_niveles_norma(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Carga elementos y tópicos-padre desde niveles_iho_norma.json.
    Retorna (elementos, topicos) donde elementos tiene códigos como 'F1.1a'
    y topicos tiene padres como 'F1.1'.
    """
    if not path.exists():
        return {}, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("elementos", {}), data.get("topicos", {})


def buscar_nivel_iho(codigo_topico: str, elementos: dict[str, str], topicos: dict[str, str]) -> str:
    """Retorna nivel IHO (B/I/A) para un código de tópico/elemento.
    Busca primero en elementos (e.g. 'H1.2a'), luego en tópicos padre ('H1.2').
    Si no encuentra, retorna 'I' (Intermediate) como valor conservador.
    """
    if codigo_topico in elementos:
        return elementos[codigo_topico]
    # Tópico padre: quitar letra final si es elemento (H1.2a → H1.2)
    padre = codigo_topico[:-1] if codigo_topico and codigo_topico[-1].isalpha() else codigo_topico
    if padre in topicos:
        return topicos[padre]
    # Fallback heurístico por familia de tópico
    familia = re.match(r"([A-Z]\d+)", codigo_topico)
    if familia:
        fam = familia.group(1)
        if fam in {"H7", "H8"}:
            return "A"
        if fam in {"H4", "H5", "H6"}:
            return "I"
    return "I"


def estimar_nivel_actual_programa(texto: str) -> str:
    """Estima el nivel que el programa cubre (B/I/A) según los verbos de los contenidos."""
    t = texto.lower()
    verbos: dict[str, list[str]] = {
        "B": ["definir", "identificar", "reconocer", "describir", "listar", "nombrar", "enumerar"],
        "I": [
            "explicar", "comprender", "analizar", "interpretar", "fundamento",
            "aplicar", "usar", "operar", "calcular", "procesar", "ejecutar",
        ],
        "A": [
            "diseñar", "integrar", "gestionar", "planificar", "sintetizar",
            "evaluar", "proponer", "proyecto", "desarrollar", "optimizar",
        ],
    }
    puntaje = {k: sum(t.count(w) for w in ws) for k, ws in verbos.items()}
    mejor = max(puntaje, key=lambda k: (puntaje[k], NIVEL_ORD[k]))
    return mejor if puntaje[mejor] > 0 else "I"


def clasificar_desfase(requerido: str, actual: str) -> str:
    r = NIVEL_ORD.get(requerido, 2)
    a = NIVEL_ORD.get(actual, 2)
    if a > r:
        return "SOBREDIMENSIONADO"
    if a < r:
        return "SUBDIMENSIONADO"
    return "ALINEADO"


def main() -> None:
    for p in [PROGRAMAS_PATH, CURRICULUM_PATH]:
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo: {p.name}")

    if not NIVELES_IHO_PATH.exists():
        raise FileNotFoundError(
            "Falta niveles_iho_norma.json — ejecuta primero extraer_niveles_iho.py"
        )

    programas_data  = load_json(PROGRAMAS_PATH).get("programas", [])
    curriculum_data = load_json(CURRICULUM_PATH)
    hojas           = curriculum_data.get("leaves", [])
    elementos, topicos_norma = cargar_niveles_norma(NIVELES_IHO_PATH)

    print(f"   Elementos IHO cargados : {len(elementos)}")
    print(f"   Tópicos padre cargados : {len(topicos_norma)}")

    programas_por_codigo = {
        p["codigo_asignatura"]: p
        for p in programas_data
        if p.get("codigo_asignatura") and not p.get("error")
    }
    codigos_norm = {normalize_code(c): c for c in programas_por_codigo}

    corpus_por_asignatura: dict[str, str] = {}
    for codigo, programa in programas_por_codigo.items():
        partes: list[str] = []
        partes.extend(programa.get("resultados_aprendizaje", []))
        for unidad in programa.get("unidades_tematicas", []):
            partes.extend(unidad.get("contenidos_especificos", []))
            partes.extend(unidad.get("actividades_asociadas", []))
        corpus_por_asignatura[codigo] = "\n".join(partes)

    filas: list[dict[str, Any]] = []
    por_asignatura: dict[str, dict[str, Any]] = {
        c: {"SOBREDIMENSIONADO": 0, "ALINEADO": 0, "SUBDIMENSIONADO": 0}
        for c in programas_por_codigo
    }

    patron_cod = re.compile(r"\b([A-Za-z]{2,10}\s?\d{3})\b")
    sin_nivel_norma: list[str] = []

    for leaf in hojas:
        codigo_iho  = str(leaf.get("codigo") or "")
        descripcion = str(leaf.get("descripcion") or "")
        topico      = str(leaf.get("topico") or "")
        asgn_texto  = str(leaf.get("asgn_shoa") or "")

        encontrados: list[str] = []
        for bruto in patron_cod.findall(asgn_texto):
            norm = normalize_code(bruto)
            if norm in codigos_norm:
                encontrados.append(codigos_norm[norm])
        encontrados = sorted(set(encontrados))
        if not encontrados:
            continue

        nivel_req = buscar_nivel_iho(codigo_iho, elementos, topicos_norma)
        if codigo_iho not in elementos and codigo_iho[:-1] not in topicos_norma:
            sin_nivel_norma.append(codigo_iho)

        niveles_actuales: list[str] = [
            estimar_nivel_actual_programa(corpus_por_asignatura.get(cod, ""))
            for cod in encontrados
        ]
        nivel_actual = (
            max(niveles_actuales, key=lambda x: NIVEL_ORD.get(x, 2))
            if niveles_actuales else "I"
        )
        clasificacion = clasificar_desfase(nivel_req, nivel_actual)

        for cod in encontrados:
            por_asignatura[cod][clasificacion] += 1

        filas.append({
            "codigo_topico_iho":    codigo_iho,
            "topico_iho":           topico,
            "descripcion":          descripcion,
            "nivel_iho_requerido":  nivel_req,
            "nivel_actual_programa": nivel_actual,
            "clasificacion":        clasificacion,
            "asignaturas_relacionadas": encontrados,
        })

    resumen = {
        "total_topicos_analizados": len(filas),
        "sobredimensionados": sum(1 for x in filas if x["clasificacion"] == "SOBREDIMENSIONADO"),
        "alineados":          sum(1 for x in filas if x["clasificacion"] == "ALINEADO"),
        "subdimensionados":   sum(1 for x in filas if x["clasificacion"] == "SUBDIMENSIONADO"),
        "sin_nivel_en_norma": len(set(sin_nivel_norma)),
        "escala_niveles":     "B=Basic < I=Intermediate < A=Advanced (IHO S-5A)",
    }

    salida = {
        "resumen":        resumen,
        "topicos":        filas,
        "por_asignatura": por_asignatura,
    }

    OUTPUT_PATH.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAnalisis de profundidad IHO generado en: {OUTPUT_PATH}")
    print(
        "Sobredimensionados: {s} | Alineados: {a} | Subdimensionados: {u} | Sin nivel norma: {n}".format(
            s=resumen["sobredimensionados"],
            a=resumen["alineados"],
            u=resumen["subdimensionados"],
            n=resumen["sin_nivel_en_norma"],
        )
    )


if __name__ == "__main__":
    main()
