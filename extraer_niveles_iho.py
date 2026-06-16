"""Extrae niveles de competencia B/I/A de la norma IHO S-5A (PDF)
y genera niveles_iho_norma.json con el mapeo elemento → nivel.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "S-5A_Ed1.0.2.pdf"
OUTPUT_JSON = BASE_DIR / "niveles_iho_norma.json"
OUTPUT_PEND = BASE_DIR / "niveles_pendientes.txt"
SHOA_REF    = BASE_DIR / "curriculum_data.json"

# Nivel más alto según IHO S-5A: A > I > B
NIVEL_ORD = {"B": 1, "I": 2, "A": 3}

# Tópicos que SHOA trabaja (del curriculum_data.json)
SHOA_TOPICOS_ESPERADOS: set[str] = set()


def nivel_max(niveles: list[str]) -> str:
    """Retorna el nivel más exigente de una lista."""
    validos = [n for n in niveles if n in NIVEL_ORD]
    if not validos:
        return "B"
    return max(validos, key=lambda n: NIVEL_ORD[n])


def extraer_niveles_pdf(pdf_path: Path) -> dict[str, str]:
    """Extrae {codigo_elemento: nivel} de la norma IHO S-5A."""
    try:
        import pdfplumber
    except ImportError:
        print("pdfplumber no instalado; intentando con pymupdf...")
        return extraer_niveles_fitz(pdf_path)

    # Patrón de elemento: F1.1a / H2.3b / B1.2c  (con o sin espacio)
    elem_pat  = re.compile(r'\b([BFH]\d+\.\d+[a-z])\b')
    # Nivel(es) en paréntesis: (B), (I), (A), (I, B), (A, I), (I,A)
    nivel_pat = re.compile(r'\(\s*([AIB](?:\s*,\s*[AIB])*)\s*\)')

    resultados: dict[str, str] = {}
    paginas_procesadas = 0

    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pgs = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""

            # Sólo páginas con elementos (F/H topics aparecen en pgs 7-34)
            if not elem_pat.search(txt):
                continue
            paginas_procesadas += 1

            # Trabajamos línea por línea
            lineas = txt.splitlines()
            ultimo_elem: str | None = None

            for linea in lineas:
                # Buscar código de elemento en esta línea
                m_elem = elem_pat.search(linea)
                if m_elem:
                    ultimo_elem = m_elem.group(1)

                # Buscar nivel(es) en esta línea
                for m_niv in nivel_pat.finditer(linea):
                    raw = m_niv.group(1)
                    letras = [x.strip().upper() for x in raw.split(",")]
                    letras = [l for l in letras if l in NIVEL_ORD]
                    if letras and ultimo_elem:
                        nivel = nivel_max(letras)
                        # Sólo actualizar si el nuevo nivel es más alto
                        if (ultimo_elem not in resultados
                                or NIVEL_ORD[nivel] > NIVEL_ORD[resultados[ultimo_elem]]):
                            resultados[ultimo_elem] = nivel

    print(f"   Páginas con tópicos procesadas: {paginas_procesadas}/{total_pgs}")
    return resultados


def extraer_niveles_fitz(pdf_path: Path) -> dict[str, str]:
    """Fallback con pymupdf si pdfplumber falla."""
    import fitz  # type: ignore

    elem_pat  = re.compile(r'\b([BFH]\d+\.\d+[a-z])\b')
    nivel_pat = re.compile(r'\(\s*([AIB](?:\s*,\s*[AIB])*)\s*\)')

    resultados: dict[str, str] = {}
    doc = fitz.open(str(pdf_path))

    for page in doc:
        txt = page.get_text()
        ultimo_elem: str | None = None
        for linea in txt.splitlines():
            m_elem = elem_pat.search(linea)
            if m_elem:
                ultimo_elem = m_elem.group(1)
            for m_niv in nivel_pat.finditer(linea):
                raw = m_niv.group(1)
                letras = [x.strip().upper() for x in raw.split(",")]
                letras = [l for l in letras if l in NIVEL_ORD]
                if letras and ultimo_elem:
                    nivel = nivel_max(letras)
                    if (ultimo_elem not in resultados
                            or NIVEL_ORD[nivel] > NIVEL_ORD[resultados[ultimo_elem]]):
                        resultados[ultimo_elem] = nivel
    return resultados


def cargar_topicos_shoa(shoa_path: Path) -> set[str]:
    """Obtiene los códigos de tópico que SHOA tiene mapeados."""
    if not shoa_path.exists():
        return set()
    data = json.loads(shoa_path.read_text(encoding="utf-8"))
    topicos: set[str] = set()
    for leaf in data.get("leaves", []):
        cod = str(leaf.get("codigo") or "")
        if cod:
            topicos.add(cod)
    return topicos


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"No se encontró el PDF: {PDF_PATH}")

    print(f"Leyendo {PDF_PATH.name} ...")
    niveles = extraer_niveles_pdf(PDF_PATH)

    if not niveles:
        raise RuntimeError("No se extrajeron niveles del PDF. Verifica el formato.")

    # Ordenar por código
    niveles_ordenados = dict(sorted(niveles.items()))

    # Enriquecer con tópico padre (sin la letra final) para fallback
    topico_nivel: dict[str, str] = {}
    for elem, niv in niveles_ordenados.items():
        parent = elem[:-1]  # F1.1a → F1.1
        if parent not in topico_nivel or NIVEL_ORD[niv] > NIVEL_ORD[topico_nivel[parent]]:
            topico_nivel[parent] = niv

    salida = {
        "metadata": {
            "fuente": PDF_PATH.name,
            "nota": (
                "Niveles de competencia IHO S-5A: "
                "B=Basic, I=Intermediate, A=Advanced. "
                "Para elementos con múltiples niveles se tomó el más alto."
            ),
            "total_elementos": len(niveles_ordenados),
            "total_topicos_padre": len(topico_nivel),
        },
        "elementos": niveles_ordenados,
        "topicos": topico_nivel,
    }
    OUTPUT_JSON.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

    # Tópicos SHOA no encontrados en la norma
    shoa_topicos = cargar_topicos_shoa(SHOA_REF)
    no_encontrados: list[str] = sorted(t for t in shoa_topicos if t not in niveles_ordenados and t not in topico_nivel)

    lines_pend = ["Tópicos SHOA sin nivel en la norma S-5A", "=" * 40]
    lines_pend += no_encontrados or ["(ninguno — todos cubiertos)"]
    OUTPUT_PEND.write_text("\n".join(lines_pend), encoding="utf-8")

    # ── Consola ──────────────────────────────────────────────────────────────
    print(f"\nPáginas procesadas : indicado arriba")
    print(f"Elementos extraídos: {len(niveles_ordenados)}")
    print(f"Tópicos padre      : {len(topico_nivel)}")
    print(f"No encontrados     : {len(no_encontrados)}")
    print(f"JSON generado      : {OUTPUT_JSON.name}")
    print(f"Pendientes         : {OUTPUT_PEND.name}")

    print("\nPrimeros 30 elementos extraídos:")
    print(f"  {'Código':<12} Nivel")
    print("  " + "-" * 20)
    for cod, niv in list(niveles_ordenados.items())[:30]:
        print(f"  {cod:<12} {niv}")

    dist = {"B": 0, "I": 0, "A": 0}
    for v in niveles_ordenados.values():
        dist[v] = dist.get(v, 0) + 1
    print(f"\nDistribución: B={dist['B']}  I={dist['I']}  A={dist['A']}")


if __name__ == "__main__":
    main()
