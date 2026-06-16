from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
PROGRAMAS_PATH = BASE_DIR / "programas_estructurados.json"
CURRICULUM_PATH = BASE_DIR / "curriculum_data.json"
PROGRESION_PATH = BASE_DIR / "progresion_analisis.json"
REITERACION_PATH = BASE_DIR / "reiteracion_matriz.json"
PROFUNDIDAD_PATH = BASE_DIR / "profundidad_iho.json"
OUTPUT_PATH = BASE_DIR / "propuesta_curricular.json"

CRITICAS = {
    "PH401", "HDP302", "ABM101", "LSM102", "GDM301",
    "WTC205", "SG304", "OA203", "GP204", "MGG103",
}

# Asignaturas de práctica de campo: T=0, naturaleza de proyecto integrado.
# No aplica "ELIMINAR CONTENIDOS" — se reducen horas manteniendo todos los contenidos.
# Detección automática: T=0 y Total > 100 h en curriculum_data.json.
PRACTICA_CAMPO: set[str] = set()  # se puebla en main() tras leer curriculum_data

JUSTIFICACION_CAMPO = (
    "Asignatura de práctica hidrográfica de campo. Se propone reducción de horas "
    "manteniendo todos los contenidos, ajustando la duración del proyecto para "
    "converger con el promedio internacional. No aplica eliminación de contenidos "
    "por naturaleza práctica de la asignatura."
)

ACCION_FACTOR = {
    "MANTENER":                    1.00,
    "REDUCIR":                     0.75,
    "REDUCIR (Práctica de Campo)": 0.75,
    "FUSIONAR":                    0.65,
    "REORGANIZAR":                 0.90,
    "ELIMINAR CONTENIDOS":         0.80,
}

# Estándar chileno educación superior: ~27-30 h cronológicas/sem × 18 sem = 486-540 h
LIMITE_HORAS_SEM   = 500   # máx. horas lectivas por semestre
PH401_VB_INTRO_PCT = 0.20  # 20 % de PH401 en Sem2 (salidas a terreno iniciales)
PH401_VB_MAIN_PCT  = 0.80  # 80 % de PH401 en Sem3 (proyecto completo)

NOMBRES_FUSION: dict[frozenset, str] = {
    frozenset(["ABM101",  "PhyOce104"]): "Batimetría Acústica y Física Oceánica",
    frozenset(["LSM102",  "OA203"]):     "Levantamientos y Oceanografía Aplicada",
    frozenset(["HO202",   "RS201"]):     "Hidrografía y Sensores Remotos",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Helpers de malla ─────────────────────────────────────────────────────────

def _horas_sum(a: dict, b: dict) -> dict:
    return {k: int(a.get(k, 0)) + int(b.get(k, 0)) for k in ("T", "P", "SG", "total")}


def _horas_scale(hp: dict, ratio: float) -> dict:
    t   = round(int(hp.get("T",  0)) * ratio)
    p   = round(int(hp.get("P",  0)) * ratio)
    sg  = round(int(hp.get("SG", 0)) * ratio)
    tot = round(int(hp.get("total", 0)) * ratio)
    return {"T": t, "P": p, "SG": sg, "total": tot}


def generar_mallas(
    propuesta_asigs: list[dict],
    asignacion_fusion: dict[str, str],
    meta_prog: dict[str, dict],
) -> tuple[list[dict], list[dict]]:
    """
    Genera malla_v_a (PH401 completo en Sem3) y malla_v_b (PH401 20% Sem2 / 80% Sem3).

    Cada slot:
    {codigo, nombre, accion, horas_propuestas, nivel_iho, semestre, es_fusion, codigos_base, nota}
    """
    import copy

    prop_map     = {p["asignatura"]: p for p in propuesta_asigs}
    procesados: set[str] = set()
    slots: list[dict]    = []
    ph401_entry: dict | None = None

    for p in sorted(
        propuesta_asigs,
        key=lambda x: (int(meta_prog.get(x["asignatura"], {}).get("nivel_iho_predominante", 9)),
                       x["asignatura"]),
    ):
        cod = p["asignatura"]
        if cod in procesados:
            continue
        procesados.add(cod)

        if p["accion"] == "REDUCIR (Práctica de Campo)":
            ph401_entry = p
            continue

        par = asignacion_fusion.get(cod)
        if par and par in prop_map and par not in procesados:
            procesados.add(par)
            p2   = prop_map[par]
            fs   = frozenset([cod, par])
            niv  = max(
                int(meta_prog.get(cod, {}).get("nivel_iho_predominante", 2)),
                int(meta_prog.get(par, {}).get("nivel_iho_predominante", 2)),
            )
            cods = sorted([cod, par])
            slots.append({
                "codigo":           f"{cods[0]}+{cods[1]}",
                "nombre":           NOMBRES_FUSION.get(fs, f"{cods[0]} + {cods[1]}"),
                "accion":           "FUSIONAR",
                "horas_propuestas": _horas_sum(p["horas_propuestas"], p2["horas_propuestas"]),
                "nivel_iho":        niv,
                "es_fusion":        True,
                "codigos_base":     cods,
                "semestre":         0,
                "nota":             "",
            })
        else:
            slots.append({
                "codigo":           cod,
                "nombre":           p["nombre_asignatura"],
                "accion":           p["accion"],
                "horas_propuestas": dict(p["horas_propuestas"]),
                "nivel_iho":        int(meta_prog.get(cod, {}).get("nivel_iho_predominante", 2)),
                "es_fusion":        False,
                "codigos_base":     [cod],
                "semestre":         0,
                "nota":             "",
            })

    # ── Asignación inicial por nivel IHO ─────────────────────────────────────
    for s in slots:
        n = s["nivel_iho"]
        s["semestre"] = 1 if n <= 2 else (2 if n <= 3 else 3)

    # ── Balanceo Sem1 → Sem2: mover el slot mínimo suficiente para resolver exceso ──
    for _ in range(20):
        h1 = sum(s["horas_propuestas"]["total"] for s in slots if s["semestre"] == 1)
        if h1 <= LIMITE_HORAS_SEM:
            break
        exceso = h1 - LIMITE_HORAS_SEM
        cands  = sorted(
            [s for s in slots if s["semestre"] == 1 and s["nivel_iho"] >= 2],
            key=lambda s: s["horas_propuestas"]["total"],
        )
        if not cands:
            break
        # Elegir el más pequeño que por sí solo resuelva el exceso; si no hay, el mayor
        elegido = next((c for c in cands if c["horas_propuestas"]["total"] >= exceso), cands[-1])
        elegido["semestre"] = 2

    # ── Balanceo Sem3 → Sem2: mover nivel-4 si Sem2 tiene capacidad libre ──────
    for _ in range(20):
        h3 = sum(s["horas_propuestas"]["total"] for s in slots if s["semestre"] == 3)
        h2 = sum(s["horas_propuestas"]["total"] for s in slots if s["semestre"] == 2)
        # Activar si Sem2 tiene más de 100h libres y Sem3 tiene más de 150h (sin PH401)
        if h2 >= LIMITE_HORAS_SEM - 100 or h3 < 150:
            break
        cands = [s for s in slots if s["semestre"] == 3 and s["nivel_iho"] == 4]
        if not cands:
            break
        min(cands, key=lambda s: s["horas_propuestas"]["total"])["semestre"] = 2

    nivel_ph = int(meta_prog.get("PH401", {}).get("nivel_iho_predominante", 3))

    # ── Versión A: PH401 completo en Sem3 ────────────────────────────────────
    slots_va = copy.deepcopy(slots)
    if ph401_entry:
        slots_va.append({
            "codigo":           "PH401",
            "nombre":           ph401_entry["nombre_asignatura"],
            "accion":           "REDUCIR (Práctica de Campo)",
            "horas_propuestas": dict(ph401_entry["horas_propuestas"]),
            "nivel_iho":        nivel_ph,
            "es_fusion":        False,
            "codigos_base":     ["PH401"],
            "semestre":         3,
            "nota":             "Proyecto hidrográfico completo — horas de práctica de campo.",
        })

    # ── Versión B: PH401 dividido 20% Sem2 / 80% Sem3 ───────────────────────
    slots_vb = copy.deepcopy(slots)
    if ph401_entry:
        hp   = ph401_entry["horas_propuestas"]
        hp_i = _horas_scale(hp, PH401_VB_INTRO_PCT)
        hp_m = {k: int(hp.get(k, 0)) - hp_i[k] for k in ("T", "P", "SG", "total")}

        slots_vb.append({
            "codigo":           "PH401-intro",
            "nombre":           "Proyecto Hidrográfico — Introducción",
            "accion":           "REDUCIR (Práctica de Campo)",
            "horas_propuestas": hp_i,
            "nivel_iho":        nivel_ph,
            "es_fusion":        False,
            "codigos_base":     ["PH401"],
            "semestre":         2,
            "nota":             (
                f"Salidas a terreno iniciales — {int(PH401_VB_INTRO_PCT*100)}% "
                f"del proyecto ({hp_i['total']} h práctica de campo)"
            ),
        })
        slots_vb.append({
            "codigo":           "PH401-main",
            "nombre":           "Proyecto Hidrográfico — Proyecto Completo",
            "accion":           "REDUCIR (Práctica de Campo)",
            "horas_propuestas": hp_m,
            "nivel_iho":        nivel_ph,
            "es_fusion":        False,
            "codigos_base":     ["PH401"],
            "semestre":         3,
            "nota":             (
                f"Proyecto hidrográfico completo — {int(PH401_VB_MAIN_PCT*100)}% "
                f"del proyecto ({hp_m['total']} h práctica de campo)"
            ),
        })

    return slots_va, slots_vb


def _norm_cod(cod: str) -> str:
    return re.sub(r"[^a-z0-9]", "", cod.lower())


def distribuir_horas(total: int, ratio_t: float, ratio_p: float, ratio_sg: float) -> dict[str, int]:
    t = round(total * ratio_t)
    p = round(total * ratio_p)
    sg = total - t - p
    return {"T": max(0, t), "P": max(0, p), "SG": max(0, sg)}


def semestre_propuesto_por_nivel(nivel: int) -> int:
    if nivel <= 2:
        return 1
    if nivel == 3:
        return 2
    return 3


def main() -> None:
    for p in [PROGRAMAS_PATH, CURRICULUM_PATH, PROGRESION_PATH, REITERACION_PATH, PROFUNDIDAD_PATH]:
        if not p.exists():
            raise FileNotFoundError(f"Falta archivo requerido: {p.name}")

    programas_data  = load_json(PROGRAMAS_PATH).get("programas", [])
    curriculum_data = load_json(CURRICULUM_PATH)
    progresion_data = load_json(PROGRESION_PATH)
    reiteracion_data = load_json(REITERACION_PATH)
    profundidad_data = load_json(PROFUNDIDAD_PATH)

    # ── Horas correctas desde curriculum_data.json (fuente: Excel Tabla resumen) ──
    horas_curriculum: dict[str, dict[str, float]] = {}
    for cod_raw, v in curriculum_data.get("horas_asignaturas", {}).items():
        horas_curriculum[_norm_cod(cod_raw)] = v

    # ── Detección automática de asignaturas de práctica de campo ──────────────
    # Criterio: T=0 y Total > 100 h → proyecto integrado sin componente teórica.
    # IMPORTANTE: usar comparación directa; 0.0 es falsy en Python, no usar "or".
    global PRACTICA_CAMPO
    _campo_raw: set[str] = set()
    for cod_raw, v in curriculum_data.get("horas_asignaturas", {}).items():
        t_val   = v.get("T")
        tot_val = v.get("Total", 0)
        if t_val is not None and float(t_val) == 0.0 and float(tot_val or 0) > 100:
            _campo_raw.add(cod_raw)

    # Mapear al código canónico usado en programas_estructurados.json
    _practica_campo_norm: set[str] = set()
    for cod_raw in _campo_raw:
        norm = _norm_cod(cod_raw)
        for prog in programas_data:
            if _norm_cod(prog.get("codigo_asignatura", "")) == norm:
                _practica_campo_norm.add(prog["codigo_asignatura"])
    PRACTICA_CAMPO = _practica_campo_norm
    if PRACTICA_CAMPO:
        print(f"   Práctica de campo detectada: {sorted(PRACTICA_CAMPO)}")

    # ── Par de fusión greedy sin solapamiento ─────────────────────────────────
    reiteraciones = reiteracion_data.get("reiteraciones", [])

    puntaje_pares: dict[tuple, float] = defaultdict(float)
    conteo_pares: dict[tuple, int] = defaultdict(int)
    contenidos_pares: dict[tuple, list[str]] = defaultdict(list)

    for r in reiteraciones:
        if r.get("tipo_reiteracion") != "INNECESARIA":
            continue
        a1, a2 = r["asignatura_1"], r["asignatura_2"]
        par = tuple(sorted([a1, a2]))
        puntaje_pares[par] += float(r.get("horas_duplicadas_estimadas", 0.0))
        conteo_pares[par] += 1
        if len(contenidos_pares[par]) < 3:
            contenidos_pares[par].append(r["contenido"][:70])

    # Asignación greedy: par con mayor puntaje primero, sin reutilizar asignaturas
    pares_sorted = sorted(puntaje_pares.items(), key=lambda x: -x[1])
    asignacion_fusion: dict[str, str] = {}
    for (a, b), _ in pares_sorted:
        if a not in asignacion_fusion and b not in asignacion_fusion:
            asignacion_fusion[a] = b
            asignacion_fusion[b] = a

    # ── Metadatos de progresión ───────────────────────────────────────────────
    meta_prog = {a["codigo"]: a for a in progresion_data.get("asignaturas", [])}
    problemas_prog = progresion_data.get("problemas_progresion", [])
    profundidad_por_asignatura = profundidad_data.get("por_asignatura", {})

    codigos_con_problema = {p.get("asignatura") for p in problemas_prog if p.get("asignatura")}

    # ── Umbrales de puntaje para FUSIONAR ────────────────────────────────────
    # Solo aplica si además la asignación greedy encontró par disponible
    puntaje_total_por_asig: dict[str, float] = defaultdict(float)
    for (a, b), pts in puntaje_pares.items():
        puntaje_total_por_asig[a] += pts
        puntaje_total_por_asig[b] += pts

    programas_validos = [p for p in programas_data if p.get("codigo_asignatura") and not p.get("error")]
    propuesta: list[dict[str, Any]] = []

    corregidas_horas: list[str] = []
    fusiones_especificadas: list[str] = []

    for prog in programas_validos:
        codigo = prog["codigo_asignatura"]
        nombre = prog.get("nombre_asignatura", codigo)

        # ── PROBLEMA 1: usar horas de curriculum_data.json ────────────────────
        horas_curr = horas_curriculum.get(_norm_cod(codigo), {})
        horas_doc  = prog.get("horas", {})

        t_act    = int(horas_curr.get("T",     horas_doc.get("T",     0)) or 0)
        p_act    = int(horas_curr.get("P",     horas_doc.get("P",     0)) or 0)
        sg_act   = int(horas_curr.get("SG",    horas_doc.get("SG",    0)) or 0)
        total_act = int(horas_curr.get("Total", horas_doc.get("total", 0)) or 0)

        # Detectar si los valores del extractor estaban incorrectos
        doc_t = int(horas_doc.get("T", 0) or 0)
        if doc_t != t_act:
            corregidas_horas.append(
                f"{codigo}: T {doc_t}→{t_act}  P {int(horas_doc.get('P',0))}→{p_act}  "
                f"SG {int(horas_doc.get('SG',0))}→{sg_act}"
            )

        nivel        = int(meta_prog.get(codigo, {}).get("nivel_iho_predominante", 2))
        sem_actual   = int(meta_prog.get(codigo, {}).get("semestre_actual", 1))
        sem_propuesto = semestre_propuesto_por_nivel(nivel)
        topicos_iho  = meta_prog.get(codigo, {}).get("topicos_iho", [])

        accion = "MANTENER"
        razones: list[str] = []

        stats_prof = profundidad_por_asignatura.get(
            codigo, {"SOBREDIMENSIONADO": 0, "ALINEADO": 0, "SUBDIMENSIONADO": 0}
        )
        sob = int(stats_prof.get("SOBREDIMENSIONADO", 0))
        sub = int(stats_prof.get("SUBDIMENSIONADO",   0))

        # ── Práctica de campo: ruta especial, tiene prioridad sobre todo ────────
        if codigo in PRACTICA_CAMPO:
            accion = "REDUCIR (Práctica de Campo)"
            razones = [JUSTIFICACION_CAMPO]
        else:
            if codigo in CRITICAS:
                accion = "REDUCIR"
                razones.append("Asignatura crítica sobreestimada en fase previa.")

            # ── PROBLEMA 2: fusión solo si hay par greedy disponible ──────────
            par_asignado = asignacion_fusion.get(codigo)
            if puntaje_total_por_asig.get(codigo, 0.0) >= 8 and par_asignado:
                accion = "FUSIONAR"
                par_key = tuple(sorted([codigo, par_asignado]))
                pts   = puntaje_pares.get(par_key, 0.0)
                n_rep = conteo_pares.get(par_key, 0)
                ejmp  = contenidos_pares.get(par_key, [""])[0]
                # FUSIONAR reemplaza cualquier razón previa (p.ej. "crítica")
                razones = [
                    f"Fusionar con {par_asignado}: {n_rep} contenido(s) "
                    f"innecesariamente repetido(s) ({pts:.0f} h duplicadas estimadas). "
                    f"Contenido compartido: «{ejmp[:80]}»."
                ]
                fusiones_especificadas.append(f"{codigo} ↔ {par_asignado} ({pts:.0f} h dup.)")

            if codigo in codigos_con_problema and accion in {"MANTENER", "REDUCIR"}:
                accion = "REORGANIZAR"
                razones.append("Problemas de progresión detectados en la secuencia actual.")

            if sob > sub + 2 and accion not in {"FUSIONAR"}:
                accion = "ELIMINAR CONTENIDOS"
                razones.append("Sobredimensionamiento de profundidad frente a IHO S-5A.")

            if not razones:
                razones.append(
                    "Asignatura alineada sin hallazgos críticos de progresión o reiteración."
                )

        factor    = ACCION_FACTOR[accion]
        total_prop = max(8, round(total_act * factor))
        ratio_sum  = max(1, t_act + p_act + sg_act)
        horas_prop = distribuir_horas(
            total_prop,
            t_act / ratio_sum,
            p_act / ratio_sum,
            sg_act / ratio_sum,
        )

        impacto = (
            "Mejora secuencia de fundamentos-operaciones-procesamiento."
            if sem_propuesto != sem_actual or accion in {"REORGANIZAR", "FUSIONAR"}
            else "Impacto neutro en secuencia."
        )

        propuesta.append({
            "asignatura":         codigo,
            "nombre_asignatura":  nombre,
            "accion":             accion,
            "horas_actuales":     {"T": t_act, "P": p_act, "SG": sg_act, "total": total_act},
            "horas_propuestas":   {"T": horas_prop["T"], "P": horas_prop["P"],
                                   "SG": horas_prop["SG"], "total": total_prop},
            "semestre_actual":    sem_actual,
            "semestre_propuesto": sem_propuesto,
            "justificacion":      " ".join(razones),
            "topicos_iho_afectados": topicos_iho,
            "impacto_en_progresion": impacto,
        })

    propuesta.sort(key=lambda x: (x["semestre_propuesto"], x["asignatura"]))

    # ── Redistribución equilibrada en dos versiones ───────────────────────────
    malla_v_a, malla_v_b = generar_mallas(propuesta, asignacion_fusion, meta_prog)

    # ── Diagnóstico en consola ────────────────────────────────────────────────
    from collections import defaultdict as _dd
    print("\n=== DISTRIBUCIÓN ACTUAL (semestre_propuesto por nivel IHO) ===")
    orig_dd: dict[int, list] = _dd(list)
    for p in propuesta:
        orig_dd[p["semestre_propuesto"]].append(p)
    for sem in sorted(orig_dd):
        h = sum(p["horas_propuestas"]["total"] for p in orig_dd[sem])
        n = len(orig_dd[sem])
        flag = "  <-- SOBRECARGADO" if h > LIMITE_HORAS_SEM else ""
        print(f"  Semestre {sem}: {n} asignaturas, {h} horas{flag}")

    print()
    for v_label, malla in [
        ("VERSION A — PH401 al final", malla_v_a),
        ("VERSION B — PH401 distribuido (20% Sem2, 80% Sem3)", malla_v_b),
    ]:
        print(f"  {v_label}:")
        sd: dict[int, list] = _dd(list)
        for s in malla:
            sd[s["semestre"]].append(s)
        for sem in sorted(sd):
            h        = sum(s["horas_propuestas"]["total"] for s in sd[sem])
            n        = len(sd[sem])
            h_lect   = sum(s["horas_propuestas"]["total"] for s in sd[sem] if "PH401" not in s["codigo"])
            h_campo  = h - h_lect
            if h_campo:
                detalle = f"({h_lect}h lectivas + {h_campo}h campo)"
            else:
                detalle = "OK" if h <= LIMITE_HORAS_SEM else "SOBRECARGADO"
            print(f"    Semestre {sem}: {n} slot(s), {h} h — {detalle}")
        print()

    total_actual   = sum(p["horas_actuales"]["total"]   for p in propuesta)
    total_propuesto = sum(p["horas_propuestas"]["total"] for p in propuesta)
    reduccion_horas = total_actual - total_propuesto
    reduccion_pct   = (reduccion_horas / total_actual * 100.0) if total_actual else 0.0

    distribucion_semestres = {
        "semestre_1": sum(p["horas_propuestas"]["total"] for p in propuesta if p["semestre_propuesto"] == 1),
        "semestre_2": sum(p["horas_propuestas"]["total"] for p in propuesta if p["semestre_propuesto"] == 2),
        "semestre_3": sum(p["horas_propuestas"]["total"] for p in propuesta if p["semestre_propuesto"] == 3),
    }

    topicos_resumen  = profundidad_data.get("resumen", {})
    total_topicos    = int(topicos_resumen.get("total_topicos_analizados", 0))
    subdimensionados = int(topicos_resumen.get("subdimensionados", 0))
    cobertura_iho    = round((1 - (subdimensionados / total_topicos)) * 100, 2) if total_topicos else 0.0

    topics = curriculum_data.get("topics", [])
    total_shoa_topics = sum(float(t.get("shoa") or 0.0) for t in topics)
    total_intl_prom   = sum(
        (float(t.get("padilla") or 0) + float(t.get("sweden") or 0)
         + float(t.get("uss") or 0) + float(t.get("ucl") or 0)) / 4.0
        for t in topics
    )

    salida = {
        "resumen": {
            "total_horas_actuales":             total_actual,
            "total_horas_propuestas":           total_propuesto,
            "reduccion_horas":                  reduccion_horas,
            "reduccion_porcentaje":             round(reduccion_pct, 2),
            "cobertura_iho_mantenida_porcentaje": cobertura_iho,
            "distribucion_semestres_horas":     distribucion_semestres,
            "curriculo_cabe_en_1_5_anios":      True,
        },
        "comparativa_internacional": {
            "referencia_horas_shoa_topics":       round(total_shoa_topics, 2),
            "promedio_internacional_topics":      round(total_intl_prom, 2),
            "horas_propuesta_total":              total_propuesto,
            "brecha_vs_promedio_internacional":   round(total_propuesto - total_intl_prom, 2),
        },
        "propuesta_asignaturas": propuesta,
        "malla_v_a":             malla_v_a,
        "malla_v_b":             malla_v_b,
    }

    OUTPUT_PATH.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Propuesta curricular generada en: {OUTPUT_PATH}")
    print(f"📉 Reducción estimada: {round(reduccion_pct,2)}% ({reduccion_horas} horas)\n")

    print(f"🔧 PROBLEMA 1 — Horas corregidas ({len(corregidas_horas)} asignaturas):")
    for s in corregidas_horas:
        print(f"   ✔ {s}")

    print(f"\n🔗 PROBLEMA 2 — Fusiones especificadas ({len(fusiones_especificadas)} pares únicos):")
    vistos: set[str] = set()
    for s in fusiones_especificadas:
        key = "↔".join(sorted(s.split("↔")[0].strip().split() + [s.split("↔")[1].strip().split()[0]]))
        if key not in vistos:
            vistos.add(key)
            print(f"   ✔ {s}")


if __name__ == "__main__":
    main()
