# Contexto de Sesión — SHOA Curriculum Design

**Fecha:** 2026-06-16  
**Proyecto:** Rediseño Curricular Programa de Hidrografía SHOA  
**Directorio:** `C:\Users\jsant\OneDrive\Desktop\shoa-curriculum-design\`

---

## Estado del Proyecto

### Archivos principales

| Archivo | Descripción | Estado |
|---|---|---|
| `app_diseno.py` | Dashboard Streamlit principal (6 tabs) | ✅ Operativo |
| `extractor_programas.py` | Lee horas desde fila TOTAL de tabla de unidades | ✅ Reescrito |
| `matriz_reiteracion.py` | Análisis fuzzy de contenidos duplicados | ✅ Con deduplicación frozenset |
| `analisis_progresion.py` | Grafo de dependencias y secuenciación | ✅ |
| `analisis_profundidad.py` | Alineación con niveles IHO B/I/A | ✅ |
| `propuesta_curricular.py` | Nueva malla Versión A y B | ✅ |
| `requirements.txt` | Dependencias para Streamlit Cloud | ✅ |
| `.streamlit/config.toml` | Tema SHOA (azul #0077C8) | ✅ |
| `setup_assets.py` | Descarga logo desde shoa.cl | ✅ |
| `.gitignore` | Excluye docx/pdf/xlsx de GitHub | ✅ |
| `README.md` | Documentación pública | ✅ |

### JSONs de datos (fuente de verdad)

| JSON | Descripción | Última actualización |
|---|---|---|
| `curriculum_data.json` | Horas por asignatura (Excel), leaves IHO, horas_asignaturas | Vigente |
| `programas_estructurados.json` | Contenido extraído de Word (horas desde fila TOTAL) | 2026-06-15 |
| `reiteracion_matriz.json` | 93 pares únicos (era 104 antes de deduplicar) | 2026-06-15 |
| `progresion_analisis.json` | Grafo de dependencias entre asignaturas | Vigente |
| `profundidad_iho.json` | Cobertura B/I/A por asignatura | Vigente |
| `propuesta_curricular.json` | Malla propuesta Versión A y B | Vigente |
| `niveles_iho_norma.json` | Norma S-5A procesada | Vigente |

---

## Trabajo Completado en Esta Sesión

### 1. Corrección bug GDM301 (T=P=AE=160)

**Problema:** `extraer_horas()` escaneaba líneas planas de tabla horizontal Word → todos los valores resultaban iguales al Total.

**Solución aplicada en `extractor_programas.py`:**
- Función `_encontrar_cols_horas()`: detecta columnas T/P/AE dinámicamente en las primeras 5 filas
- Función `_es_fila_total()`: busca "TOTAL" en TODAS las celdas (no solo las primeras 4)
- `extraer_unidades_tabla()` devuelve `dict {"T": t, "P": p, "SG": ae, "total": t+p+ae}` desde fila TOTAL
- Fuente de horas: fila TOTAL de tabla de unidades (no tabla resumen superior)
- `tab_validacion()` en app usa `curriculum_data.json` como fuente primaria (Excel), Word como secundaria

**Resultado:** GDM301 muestra correctamente T=54h / P=100h / AE=6h / Total=160h

### 2. Deduplicación de pares en matriz de reiteración

**Problema:** Algoritmo generaba par A→B y B→A como registros separados.

**Solución en `matriz_reiteracion.py`:**
```python
par_key: frozenset = frozenset([
    (c1["codigo"], c1["contenido"]),
    (c2["codigo"], c2["contenido"]),
])
if par_key in pares_vistos: continue
```

**Resultado:** 104 pares brutos → 93 pares únicos

### 3. Publicación en Streamlit Cloud

**Archivos creados:** `requirements.txt`, `.gitignore`, `.streamlit/config.toml`, `README.md`, `setup_assets.py`

**Cambios en `app_diseno.py`:**
- Sidebar con logo SHOA, versión de datos, modo Online
- `_aviso_script()` amigable para modo cloud (sin instrucciones de terminal)
- `_get_h()` helper para variantes de mayúsculas en claves del JSON

**Git:** Repositorio inicializado y pusheado a `github.com/jsantistavilo-maker/shoa-curriculum-design`

### 4. Análisis de Justificación Académica (completado en esta sesión)

Ver sección detallada abajo.

---

## Justificación Académica — Fusiones Propuestas

### Resumen ejecutivo

| Par | H actuales | H fusionadas | H recuperables | INNECESARIAS | Tópico IHO | Recomendación |
|---|---|---|---|---|---|---|
| ABM101 + PhyOce104 | 280h | 240–260h | ~20–40h | 1 par (18h) | H2↔F2 (semántico) | ✅ Fusionar |
| HO202 + RS201 | 241h | 200–220h | ~20–40h | 2 pares (57.6h) | H4: Survey Operations | ✅ Fusionar |
| LSM102 + OA203 | 222h | 190–200h | ~22–30h | 4 pares (28.8h) | F1: Earth Models | ✅ Fusionar* |

*Sujeto a resolución de secuencia temporal Sem 1 → Sem 2.

**Total horas recuperables: ~62–110h** redistribuibles a PH401 o prácticas.

---

### PAR 1: ABM101 + PhyOce104

**ABM101** (T=98/P=69/SG=13 = 180h, Sem 1): H1-Positioning, H2-Underwater Sensors, H6-Hydro Data Acquisition  
**PhyOce104** (T=51/P=45/SG=4 = 100h, Sem 1): F2-Oceanography

**Contenidos compartidos (6 pares únicos):**
- "Mediciones de velocidad del sonido" ↔ "Ecuaciones de velocidad del sonido" — 91% INNECESARIA (18h)
- Perfil/gradiente/capas de velocidad del sonido ↔ Ecuaciones VS — 81% REVISAR (×3)
- Mediciones offset con sensores ↔ Sensores oceanográficos — 80% REVISAR
- Canal del sonido ↔ Ecuaciones VS — 77% REVISAR

**Conclusión:** Fusionar. El sonido en el agua es el nexo físico estructural. PhyOce104 enseña la física (F2.1b Physical properties of seawater), ABM101 la aplica (H2). En paralelo en Sem 1 no puede darse la secuencia teoría→aplicación. Nombre sugerido: *"Oceanografía Física Aplicada y Métodos Batimétricos Acústicos"*, ~240–260h, Sem 1.

---

### PAR 2: HO202 + RS201

**HO202** (T=84/P=66/SG=10 = 160h, Sem 2): H4-Survey Operations  
**RS201** (T=44/P=35/SG=2 = 81h, Sem 2): H3-LiDAR and Remote Sensing, H4-Survey Operations

**Tópico IHO compartido:** H4 (Survey Operations and Applications)  
**Subtópicos H4 compartidos:** H4.2e Airborne LiDAR (RS201), H4.3a Classification from acoustic data (HO202+RS201)

**Contenidos compartidos (5 pares):**
- "Técnicas y requerimientos de calibración" ↔ "Técnicas de calibración y requerimientos" — **100%** INNECESARIA (28.8h)
- "Detección de objetos" ↔ "Influencia geometría...detección de objetos" — **100%** INNECESARIA (28.8h)
- Espaciamiento líneas, orientación — 83% REVISAR (12h)
- Modelos de imprecisiones — 80% REVISAR (12h)
- Cobertura del barrido — 76% REVISAR (12h)

**Horas duplicadas estimadas: 93.6h (38.8% del total combinado)**

**Conclusión:** Fusionar. Ambas son "survey operations" con sensores distintos (acústico vs LiDAR). La estructura fusionada se organiza por etapa (planificación→calibración→adquisición→QC), los sensores son instancias del mismo proceso. Nombre sugerido: *"Métodos de Levantamiento Hidrográfico"*, ~200–220h, Sem 2.

---

### PAR 3: LSM102 + OA203

**LSM102** (T=56/P=59/SG=7 = 122h, Sem 1): F1-Earth Models  
**OA203** (T=47/P=50/SG=3 = 100h, Sem 2): F1-Earth Models, H6-Hydro Data Acquisition

**Tópico IHO compartido:** F1 (Earth Models)  
**Subtópico F1 compartido:** F1.6b Theory of observations (51h total, ambas asignaturas)

**Contenidos compartidos (5 pares, 4 INNECESARIA — mayor proporción):**
- "Exactitud, precisión, confiabilidad, repetibilidad" ↔ "Noción de incertidumbre..." — **100%** INNECESARIA (7.2h)
- "Noción de incertidumbre relacionada con observaciones" ↔ ídem — 96% INNECESARIA (×2, 7.2h c/u)
- "Propagación de la incertidumbre" ↔ "Propagación de incertidumbres" — 96% INNECESARIA (7.2h)
- "Exactitud, precisión..." ↔ "Noción de incertidumbre..." — 82% REVISAR (3h)

**Horas duplicadas estimadas: 31.8h**

**Conclusión:** Fusionar con condición. Mayor densidad INNECESARIA (80%) de los 3 pares. La teoría de observaciones se enseña dos veces sin diferenciación de profundidad. **Factor complicador:** LSM102 Sem 1, OA203 Sem 2 — la fusión requiere decidir ubicación. Alternativa: restructuración coordinada (LSM102 retira contenidos de incertidumbre; OA203 los recibe con mayor rigor reconociendo lo previo). Nombre sugerido: *"Geodesia y Ajuste de Observaciones"*, ~190–200h, Sem 1-2 o Sem 2.

---

## Pendientes

- [ ] **GDM301**: Archivo Word intermitentemente bloqueado por OneDrive. Cuando esté disponible, re-correr `extractor_programas.py` para incluirlo en `programas_estructurados.json`.
- [ ] **Actualizar README.md**: Reemplazar `TU_LINK_AQUI` con URL real de Streamlit Cloud una vez deployado.
- [ ] **Logo SHOA**: Colocar manualmente en `assets/logo_shoa.png` si `setup_assets.py` no pudo descargarlo.
- [ ] **Streamlit Cloud deploy**: Configurar en share.streamlit.io apuntando a `jsantistavilo-maker/shoa-curriculum-design`, branch `main`, entry point `app_diseno.py`.

---

## Constantes Técnicas Clave

```python
# curriculum_data.json
horas_asignaturas["ABM 101"]  # clave con espacio, ej: "ABM 101" no "ABM101"
leaves[i]["asgn_shoa"]        # formato: "ABM 101 T.U. 1.2 (i-iv)"

# Tópicos IHO
# F1: Earth Models | F2: Oceanography | F3: Geology & Geophysics
# H1: Positioning | H2: Underwater Sensors | H3: LiDAR & Remote Sensing
# H4: Survey Operations | H5: Water Levels | H6: Hydro Data Acquisition
# H7: Data Management | H8: Legal Aspects

# Niveles IHO: B=Basic(1) < I=Intermediate(2) < A=Advanced(3)

# Fuzzy threshold: 75 (token_set_ratio)
# INNECESARIA: similitud>=90 AND nivel diff<=1 AND sem diff<=1
# JUSTIFICADA: nivel_2>nivel_1 AND contiene keyword de profundización
# REVISAR: resto
```

---

## Seguridad / Confidencialidad

**NUNCA subir a GitHub:**
- `programas/` (Word .docx originales)
- `*.pdf` (norma IHO S-5A)
- `*.xlsx`, `*.xls` (planilla Excel malla)

**Sí publicar:** solo los JSON de datos procesados (ver `.gitignore`)

---

*Generado: 2026-06-16 | Claude Code + Sonnet 4.6*
