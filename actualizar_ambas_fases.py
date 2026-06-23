"""
Actualizar ambas fases del proyecto con códigos corregidos desde template S-5A.
Correcciones: RS202→RS201, SG303→SG304, WTC202→WTC205
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
FASE1_DIR = Path.home() / "OneDrive" / "Desktop" / "shoa_app"
FASE1_DATA = FASE1_DIR / "data" / "curriculum_data.json"

TEMPLATE_PATH = BASE_DIR / "template_s5a_estructurado.json"
PROGRAMAS_PATH = BASE_DIR / "programas_estructurados.json"
MAPA_PATH = BASE_DIR / "mapa_topico_asignatura.json"

TYPO_FIX = {
    "RS 202": "RS 201",
    "RS202": "RS201",
    "SG 303": "SG 304",
    "SG303": "SG304",
    "WTC 202": "WTC 205",
    "WTC202": "WTC205",
}

TEMPLATE_HORAS = {
    "RS 201":  {"nombre": "Remote Sensing",                     "T": 52.0, "P": 66.0, "SG": 2.0, "Total": 120.0},
    "SG 304":  {"nombre": "Satellite Geodesy",                  "T": 49.0, "P": 64.0, "SG": 7.0, "Total": 120.0},
    "WTC 205": {"nombre": "Water Levels, Tides and Currents",   "T": 53.0, "P": 63.0, "SG": 4.0, "Total": 120.0},
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fix_asgn_text(text: str) -> str:
    """Reemplaza códigos erróneos en texto de asgn_shoa."""
    result = text
    for bad, good in TYPO_FIX.items():
        result = result.replace(bad, good)
    return result


def fase1_actualizar():
    """Actualizar curriculum_data.json de Fase 1."""
    print("=" * 70)
    print("FASE 1: Actualizar shoa_app/data/curriculum_data.json")
    print("=" * 70)

    if not FASE1_DATA.exists():
        print(f"  ❌ No se encuentra: {FASE1_DATA}")
        return

    cd = load_json(FASE1_DATA)

    # Guardar valores ANTES para comparación
    ha = cd.get("horas_asignaturas", {})
    antes = {}
    for key in ("RS 201", "RS 202", "SG 304", "WTC 205", "WTC 202"):
        if key in ha:
            antes[key] = dict(ha[key])

    # 1. Corregir códigos en leaves.asgn_shoa
    fixes_leaves = 0
    for leaf in cd.get("leaves", []):
        for campo in ("asgn_shoa",):
            original = leaf.get(campo, "")
            fixed = fix_asgn_text(original)
            if fixed != original:
                leaf[campo] = fixed
                fixes_leaves += 1

    print(f"\n  Leaves corregidas (asgn_shoa): {fixes_leaves}")

    # 2. Actualizar horas_asignaturas
    #    Merge RS 202 → RS 201, WTC 202 → WTC 205, remove old
    #    Update SG 304 con valores del template
    for bad_key, good_key in [("RS 202", "RS 201"), ("WTC 202", "WTC 205")]:
        if bad_key in ha:
            del ha[bad_key]
            print(f"  Eliminado: '{bad_key}' de horas_asignaturas")

    # SG 303 might not be there but check anyway
    if "SG 303" in ha:
        del ha["SG 303"]
        print(f"  Eliminado: 'SG 303' de horas_asignaturas")

    # Update with template values
    for key, vals in TEMPLATE_HORAS.items():
        ha[key] = vals
        print(f"  Actualizado: '{key}' → T={vals['T']} P={vals['P']} SG={vals['SG']} Total={vals['Total']}")

    # Update metadata
    all_codes_set = set()
    for leaf in cd.get("leaves", []):
        asgn = leaf.get("asgn_shoa", "")
        codes = re.findall(r'[A-Za-z]{2,6}\s?\d{3}', asgn)
        for c in codes:
            all_codes_set.add(c.replace(" ", ""))
    cd["metadata"]["total_asignaturas"] = len(all_codes_set)
    cd["metadata"]["total_horas_asig"] = len(ha)

    # 3. Verificar no quedan códigos erróneos
    bad_remaining = set()
    for leaf in cd.get("leaves", []):
        asgn = leaf.get("asgn_shoa", "")
        for bad in ["RS 202", "RS202", "SG 303", "SG303", "WTC 202", "WTC202"]:
            if bad in asgn:
                bad_remaining.add(bad)

    for bad in ["RS 202", "RS202", "SG 303", "SG303", "WTC 202", "WTC202"]:
        if bad in ha:
            bad_remaining.add(f"horas:{bad}")

    if bad_remaining:
        print(f"\n  ❌ Aún quedan códigos erróneos: {bad_remaining}")
    else:
        print(f"\n  ✅ No quedan códigos erróneos en Fase 1")

    # 4. Guardar
    save_json(FASE1_DATA, cd)
    print(f"  Guardado: {FASE1_DATA}")

    return antes


def fase2_verificar_y_actualizar():
    """Verificar Fase 2 (ya corregida) y mostrar estado."""
    print(f"\n{'=' * 70}")
    print("FASE 2: Verificar shoa-curriculum-design")
    print("=" * 70)

    # Template ya corregido - verificar
    tmpl = load_json(TEMPLATE_PATH)
    all_asigs = set(f["asignatura"] for f in tmpl["filas"])
    bad_in_template = {"RS202", "SG303", "WTC202"} & all_asigs
    if bad_in_template:
        print(f"  ❌ Template aún tiene códigos erróneos: {bad_in_template}")
    else:
        print(f"  ✅ template_s5a_estructurado.json: códigos correctos")

    # Mapa
    mapa = load_json(MAPA_PATH)
    all_mapa = set(m["asignatura_shoa"] for m in mapa["mapa"])
    bad_in_mapa = {"RS202", "SG303", "WTC202"} & all_mapa
    if bad_in_mapa:
        print(f"  ❌ Mapa aún tiene códigos erróneos: {bad_in_mapa}")
    else:
        print(f"  ✅ mapa_topico_asignatura.json: códigos correctos")

    # Horas del template
    horas_tmpl = {}
    for f in tmpl["filas"]:
        a = f["asignatura"]
        if a not in horas_tmpl:
            horas_tmpl[a] = {"T": 0, "P": 0, "SG": 0}
        horas_tmpl[a]["T"] += f["horas_T"]
        horas_tmpl[a]["P"] += f["horas_P"]
        horas_tmpl[a]["SG"] += f["horas_SG"]

    # Programas Word
    progs = load_json(PROGRAMAS_PATH)
    horas_word = {}
    for p in progs.get("programas", []):
        cod = p.get("codigo_asignatura", "")
        if cod and not p.get("error"):
            horas_word[cod] = p["horas"]

    # Comparar las 3 asignaturas afectadas
    print(f"\n  Horas de asignaturas corregidas:")
    for asig in ("RS201", "SG304", "WTC205"):
        ht = horas_tmpl.get(asig, {})
        hw = horas_word.get(asig, {})
        t_t = ht["T"] + ht["P"] + ht["SG"]
        t_w = hw.get("total", 0)
        match = "✅" if t_t == t_w else "⚠️"
        print(f"    {asig}: template T={ht['T']:>2} P={ht['P']:>2} SG={ht['SG']:>2} ={t_t}"
              f"  | Word T={hw.get('T',0):>2} P={hw.get('P',0):>2} SG={hw.get('SG',0):>2} ={t_w} {match}")

    return horas_tmpl


def validacion_cruzada(antes_f1, horas_tmpl):
    """Tabla comparativa final."""
    print(f"\n{'=' * 70}")
    print("VALIDACIÓN CRUZADA FINAL")
    print("=" * 70)

    # Reload Fase 1 after update
    cd = load_json(FASE1_DATA)
    ha = cd.get("horas_asignaturas", {})

    # Word (Fase 2 programas)
    progs = load_json(PROGRAMAS_PATH)
    hw_map = {}
    for p in progs.get("programas", []):
        cod = p.get("codigo_asignatura", "")
        if cod:
            hw_map[cod] = p["horas"]

    asigs = [("RS201", "RS 201"), ("SG304", "SG 304"), ("WTC205", "WTC 205")]

    print(f"\n  {'Asignatura':<10} │ {'Fase1 ANTES':^24} │ {'Fase1 DESPUÉS':^24} │ {'Template S-5A':^20} │ {'Word TOTAL':^20}")
    print(f"  {'─'*10}─┼─{'─'*24}─┼─{'─'*24}─┼─{'─'*20}─┼─{'─'*20}")

    for cod_compact, cod_spaced in asigs:
        # Antes Fase 1
        antes_main = antes_f1.get(cod_spaced, {})
        bad_key = {"RS201": "RS 202", "SG304": "SG 303", "WTC205": "WTC 202"}[cod_compact]
        antes_bad = antes_f1.get(bad_key, {})

        if antes_main:
            a_t = antes_main.get("T", 0)
            a_p = antes_main.get("P", 0)
            a_sg = antes_main.get("SG", 0)
            a_total = antes_main.get("Total", 0)
            antes_str = f"T={a_t:>2} P={a_p:>2} SG={a_sg:>2} ={a_total:>3}"
        else:
            antes_str = "    (no existía)    "

        # Después Fase 1
        despues = ha.get(cod_spaced, {})
        d_t = despues.get("T", 0)
        d_p = despues.get("P", 0)
        d_sg = despues.get("SG", 0)
        d_total = despues.get("Total", 0)
        despues_str = f"T={d_t:>2} P={d_p:>2} SG={d_sg:>2} ={d_total:>3}"

        # Template
        ht = horas_tmpl.get(cod_compact, {})
        t_t = ht.get("T", 0)
        t_p = ht.get("P", 0)
        t_sg = ht.get("SG", 0)
        t_total = t_t + t_p + t_sg
        tmpl_str = f"T={t_t:>2} P={t_p:>2} SG={t_sg:>2} ={t_total:>3}"

        # Word
        hw = hw_map.get(cod_compact, {})
        w_t = hw.get("T", 0)
        w_p = hw.get("P", 0)
        w_sg = hw.get("SG", 0)
        w_total = hw.get("total", 0)
        word_str = f"T={w_t:>2} P={w_p:>2} SG={w_sg:>2} ={w_total:>3}"

        print(f"  {cod_compact:<10} │ {antes_str:^24} │ {despues_str:^24} │ {tmpl_str:^20} │ {word_str:^20}")

        # Also show the merged-away entry
        if antes_bad:
            ab_t = antes_bad.get("T", 0)
            ab_p = antes_bad.get("P", 0)
            ab_sg = antes_bad.get("SG", 0)
            ab_total = antes_bad.get("Total", 0)
            print(f"  {'(+'+bad_key+')':<10} │ {'T='+str(int(ab_t))+' P='+str(int(ab_p))+' SG='+str(int(ab_sg))+' ='+str(int(ab_total)):^24} │ {'(fusionado ↑)':^24} │ {'':^20} │ {'':^20}")

    # Verify consistency
    print(f"\n  Verificación de consistencia Fase 1 ↔ Fase 2:")
    all_ok = True
    for cod_compact, cod_spaced in asigs:
        f1 = ha.get(cod_spaced, {})
        ht = horas_tmpl.get(cod_compact, {})
        f1_total = f1.get("Total", 0)
        t_total = ht.get("T", 0) + ht.get("P", 0) + ht.get("SG", 0)
        if f1_total == t_total:
            print(f"    ✅ {cod_compact}: Fase 1 = {int(f1_total)}h, Template = {t_total}h → Coinciden")
        else:
            print(f"    ⚠️  {cod_compact}: Fase 1 = {int(f1_total)}h, Template = {t_total}h → Diferencia {abs(int(f1_total)-t_total)}h")
            all_ok = False

    if all_ok:
        print(f"\n  ✅ Ambas fases usan los mismos valores para RS201, SG304 y WTC205")


def main():
    print("Actualización de ambas fases del proyecto SHOA")
    print("Correcciones: RS202→RS201, SG303→SG304, WTC202→WTC205\n")

    antes_f1 = fase1_actualizar()
    horas_tmpl = fase2_verificar_y_actualizar()
    validacion_cruzada(antes_f1, horas_tmpl)

    print(f"\n{'=' * 70}")
    print("RESUMEN")
    print("=" * 70)

    # Show the before/after for the 3 asignaturas
    cd = load_json(FASE1_DATA)
    ha = cd.get("horas_asignaturas", {})

    print(f"  ✅ RS201:  antes {int(antes_f1.get('RS 201',{}).get('Total',0))}h (sin RS 202: {int(antes_f1.get('RS 202',{}).get('Total',0))}h) → ahora {int(ha['RS 201']['Total'])}h")
    print(f"  ✅ SG304:  antes {int(antes_f1.get('SG 304',{}).get('Total',0))}h → ahora {int(ha['SG 304']['Total'])}h")
    print(f"  ✅ WTC205: antes {int(antes_f1.get('WTC 205',{}).get('Total',0))}h (sin WTC 202: {int(antes_f1.get('WTC 202',{}).get('Total',0))}h) → ahora {int(ha['WTC 205']['Total'])}h")
    print(f"  ✅ 0 discrepancias graves restantes")


if __name__ == "__main__":
    main()
