# ESTADO DEL PROYECTO — SHOA Curriculum Design

**Última actualización:** 2026-06-16  
**Directorio:** `C:\Users\jsant\OneDrive\Desktop\shoa-curriculum-design\`  
**Repositorio:** `github.com/jsantistavilo-maker/shoa-curriculum-design`

---

## 1. Comandos para Retomar

```powershell
cd "C:\Users\jsant\OneDrive\Desktop\shoa-curriculum-design"
streamlit run app_diseno.py
```

Para regenerar todos los datos desde cero (requiere archivos Word/PDF/Excel locales):

```powershell
py extractor_programas.py    # 1°: extrae contenido de programas Word
py analisis_progresion.py    # 2°: grafo de dependencias
py matriz_reiteracion.py     # 3°: detección de contenidos duplicados
py analisis_profundidad.py   # 4°: alineación con niveles IHO
py propuesta_curricular.py   # 5°: genera propuesta de nueva malla
```

---

## 2. Lista de Archivos y su Función

### Scripts Python

| Archivo | Función | Fuentes | Genera |
|---|---|---|---|
| `extractor_programas.py` | Lee programas Word `.docx`, extrae unidades temáticas y horas desde fila TOTAL | `programas/*.docx` | `programas_estructurados.json` |
| `analisis_progresion.py` | Construye grafo de dependencias, asigna semestres y niveles IHO | `programas_estructurados.json`, `niveles_iho_norma.json` | `progresion_analisis.json` |
| `matriz_reiteracion.py` | Compara contenidos con fuzzy matching (threshold=75%), detecta duplicados | `programas_estructurados.json`, `progresion_analisis.json` | `reiteracion_matriz.json` |
| `analisis_profundidad.py` | Calcula cobertura de niveles B/I/A por asignatura según norma S-5A | `curriculum_data.json`, `niveles_iho_norma.json` | `profundidad_iho.json` |
| `propuesta_curricular.py` | Genera malla propuesta (Versión A y B) con fusiones | todos los JSON | `propuesta_curricular.json` |
| `extraer_niveles_iho.py` | Extrae niveles B/I/A desde PDF de la norma IHO S-5A | `IHO_S-5A.pdf` | `niveles_iho_norma.json` |
| `generar_word.py` | Exporta propuesta curricular a documento Word | `propuesta_curricular.json` | `Propuesta_Curricular_SHOA.docx` |
| `app_diseno.py` | Dashboard Streamlit — 6 tabs de análisis | todos los JSON | — |
| `setup_assets.py` | Descarga logo SHOA desde shoa.cl | Internet | `assets/logo_shoa.png` |

### Archivos de Configuración

| Archivo | Función |
|---|---|
| `requirements.txt` | Dependencias Python para Streamlit Cloud |
| `.gitignore` | Excluye documentos institucionales (Word/PDF/Excel) de GitHub |
| `.streamlit/config.toml` | Tema visual SHOA (azul #0077C8) |
| `README.md` | Documentación pública del repositorio |
| `contexto_sesion.md` | Resumen detallado de la sesión 2026-06-16 |

### JSONs de Datos (fuente de verdad)

| Archivo | Contenido | Registros |
|---|---|---|
| `curriculum_data.json` | Horas por asignatura (desde Excel), leaves IHO S-5A mapeados | 16 asignaturas, 4 campos de horas |
| `programas_estructurados.json` | Unidades temáticas y contenidos específicos extraídos de Word | 13 OK + 1 con error (GDM301) |
| `progresion_analisis.json` | Semestres, niveles IHO, tópicos por asignatura | 13 asignaturas (GDM301 ausente) |
| `reiteracion_matriz.json` | Pares de contenidos similares, tipo y horas duplicadas | 93 pares únicos |
| `profundidad_iho.json` | Cobertura B/I/A por asignatura y por tópico | por asignatura + por tópico |
| `propuesta_curricular.json` | Nueva malla Versión A (3 sem) y Versión B (3 sem + PH401 split) | 10 cursos V-A, 11 cursos V-B |
| `niveles_iho_norma.json` | Niveles exigidos por IHO S-5A para cada subtópico | todos los subtópicos S-5A |

---

## 3. Estado de Cada Módulo

### Dashboard (`app_diseno.py`)
**✅ Completado y funcionando**
- 6 tabs operativos: Mapa Progresión / Matriz Reiteración / Profundidad IHO / Propuesta Curricular / Exportar Word / Validación
- Modo Online: lee solo desde JSON, sin dependencias de archivos locales
- Sidebar con logo SHOA, versión de datos, modo de ejecución
- Archivos de deployment para Streamlit Cloud listos (`requirements.txt`, `config.toml`)

### Extractor de Programas (`extractor_programas.py`)
**⚠️ Completado con advertencias pendientes**
- ✅ Lee horas desde fila TOTAL del desagregado de unidades (no tabla resumen superior)
- ✅ Detección dinámica de columnas T/P/AE (tablas 7-col, 9-col, 11-col)
- ✅ 13/14 asignaturas extraídas correctamente
- ⚠️ **GDM301**: falla con `PermissionError` — archivo Word bloqueado por OneDrive/Word. Solución: cerrar el archivo en Word y re-ejecutar

### Análisis de Progresión (`analisis_progresion.py`)
**⚠️ Completado con advertencias pendientes**
- ✅ 13 asignaturas con semestres y tópicos IHO asignados
- ❌ **`dependencias[]` está vacío** — los prerrequisitos entre asignaturas no están mapeados en el JSON (el grafo no tiene aristas). El tab "Mapa de Progresión" muestra nodos pero no conexiones reales.
- ⚠️ **Niveles IHO fuera de escala**: HDP302=4 y LR303=5 (escala válida: B=1, I=2, A=3). Causa probable: `analisis_progresion.py` calcula un promedio ponderado que puede superar 3. Requiere cap en 3.

### Matriz de Reiteración (`matriz_reiteracion.py`)
**✅ Completado y funcionando**
- ✅ 93 pares únicos (deduplicación A↔B con `frozenset` aplicada)
- ✅ 13 pares INNECESARIA, 209.4h recuperables estimadas
- ⚠️ Artefacto de extracción: algunos contenidos aparecen con y sin punto final como si fueran textos distintos (ej.: "Mediciones de velocidad del sonido." vs "…sonido"), generando pares conceptualmente duplicados que el frozenset no elimina porque los strings son distintos. No afecta la validez del análisis pero infla levemente los conteos.

### Análisis de Profundidad IHO (`analisis_profundidad.py`)
**✅ Completado y funcionando**
- Cobertura por tópico y por asignatura según norma S-5A
- GDM301 ausente del análisis (sin programa extraído)

### Propuesta Curricular (`propuesta_curricular.py`)
**✅ Completado y funcionando**
- Versión A: 3 semestres, 10 asignaturas (3 fusiones aplicadas)
- Versión B: 3 semestres, PH401 dividido en intro (Sem 2) + proyecto completo (Sem 3)

### Generador Word (`generar_word.py`)
**⚠️ Completado con advertencias pendientes**
- Genera `Propuesta_Curricular_SHOA.docx` (excluido de GitHub por `.gitignore`)
- No verificado con los últimos datos regenerados — re-ejecutar antes de presentar

---

## 4. Errores Pendientes por Resolver

### ERROR 1: GDM301 — Permission Denied (❌ sin resolver)
**Síntoma:** `extractor_programas.py` falla al abrir `programas/GDM301.docx`  
**Causa:** Archivo bloqueado por Microsoft Word o OneDrive en sincronización  
**Impacto:** GDM301 ausente de `programas_estructurados.json`, `progresion_analisis.json` y `reiteracion_matriz.json`  
**Solución:**
```
1. Cerrar GDM301.docx en Microsoft Word
2. Esperar que OneDrive termine de sincronizar (ícono en bandeja)
3. py extractor_programas.py
4. Si persiste: copiar el .docx a otra carpeta fuera de OneDrive y re-ejecutar
```

### ERROR 2: Niveles IHO fuera de escala (⚠️ menor)
**Síntoma:** HDP302 tiene `nivel_iho_predominante=4` y LR303 tiene `nivel_iho_predominante=5`  
**Escala válida:** B=1, I=2, A=3 (máximo 3)  
**Causa:** `analisis_progresion.py` probablemente promedia o cuenta tópicos sin cap  
**Impacto:** El tab "Profundidad IHO" puede mostrar barras fuera de rango para estas asignaturas  
**Solución:** En `analisis_progresion.py`, aplicar `min(nivel_calculado, 3)` al asignar `nivel_iho_predominante`

### ERROR 3: Prerrequisitos no mapeados en progresion_analisis.json (⚠️ sin resolver)
**Síntoma:** `dependencias: []` vacío — el grafo no tiene aristas  
**Impacto:** El "Mapa de Progresión" muestra asignaturas como nodos sin conexión entre sí  
**Causa:** Los prerrequisitos oficiales no fueron ingresados al script (pendiente de sección 6 abajo)  
**Solución:** Ver sección 6 — ingresar prereqs en `analisis_progresion.py` y regenerar

### ERROR 4: Artefacto punto final en contenidos (⚠️ cosmético)
**Síntoma:** Algunos contenidos aparecen duplicados en la matriz con y sin punto final  
**Ejemplo:** `"Mediciones de velocidad del sonido."` y `"Mediciones de velocidad del sonido"` como dos entradas distintas  
**Causa:** Word almacena algunos párrafos con y sin punto; python-docx los lee literalmente  
**Impacto:** Leve inflación en conteo de reiteraciones (estimado: ~10 pares adicionales)  
**Solución:** En `matriz_reiteracion.py` al construir `contenidos`, normalizar: `t = t.rstrip(".").strip()`

---

## 5. Decisiones Tomadas — No Revertir

| Decisión | Detalle | Razón |
|---|---|---|
| **AE = Auto Estudio** | El campo `SG` en los datos equivale a "Auto Estudio" (antes llamado "SG = Seminario Guiado"). No cambiar el nombre del campo en JSON para no romper el código. | Terminología correcta del SHOA |
| **Horas desde fila TOTAL del desagregado** | `extractor_programas.py` ignora la tabla resumen superior y lee T/P/AE desde la fila TOTAL al fondo de la tabla de unidades temáticas | La tabla resumen tiene errores de transcripción; el desagregado es la fuente fidedigna |
| **`curriculum_data.json` como fuente primaria de horas** | En `tab_validacion()`, las horas mostradas son del Excel (campo `horas_asignaturas`), no del Word extraído | El Excel es la planilla oficial de la institución |
| **PH401 = Práctica de Campo** | PH401 (Proyecto Hidrográfico) clasificado como práctica integradora, no como asignatura de aula. T=0h, P=534h, SG=208h, Total=742h. | Es una práctica de levantamiento hidrográfico real, no tiene clases teóricas |
| **Deduplicación frozenset** | `matriz_reiteracion.py` usa `frozenset` para que A→B y B→A cuenten como un solo par | Sin esto el conteo era el doble (104 pares brutos → 93 únicos) |
| **Escala IHO: B=1, I=2, A=3** | Los niveles se almacenan como enteros 1/2/3 en el JSON | Facilita cálculos de promedio y comparación |
| **Fusiones propuestas (Versión A y B)** | ABM101+PhyOce104 / HO202+RS201 / LSM102+OA203 (ver sección 7) | Basado en análisis de reiteración y tópicos IHO compartidos |
| **Documentos institucionales fuera de GitHub** | `.gitignore` excluye `programas/`, `*.docx`, `*.pdf`, `*.xlsx` | Confidencialidad institucional SHOA |
| **RS202 y WTC202 en curriculum_data pero sin programa** | Aparecen en el Excel pero no tienen archivo Word ni análisis | Son versiones antiguas/paralelas de RS201 y WTC205. No incluir en propuesta. |

---

## 6. Prerrequisitos Oficiales de la Malla

> **⚠️ PENDIENTE CRÍTICO:** Los prerrequisitos reales de la malla no están mapeados en `analisis_progresion.py`.  
> El campo `prerrequisitos: []` está vacío para todas las asignaturas.  
> Cuando se tenga la lista oficial, agregar en `analisis_progresion.py` en la función que construye el grafo.

**Secuencia semestral actual (malla vigente):**

| Semestre | Asignaturas |
|---|---|
| Semestre 1 | ABM101, LSM102, MGG103, PhyOce104 |
| Semestre 2 | GP204, HO202, OA203, RS201, WTC205 |
| Semestre 3 | GDM301, HDP302, SG304 |
| Semestre 4 | LR303, PH401 |

**Dependencias lógicas implícitas (sin confirmar oficialmente):**

| Asignatura | Debería requerir |
|---|---|
| HO202 | ABM101, LSM102 |
| HDP302 | ABM101, HO202 |
| GP204 | LSM102 |
| SG304 | GP204 |
| GDM301 | HDP302 |
| PH401 | Todas las anteriores |
| OA203 | LSM102 |

> Para ingresar los prerrequisitos oficiales al sistema, editar `analisis_progresion.py`  
> en la sección donde se construye `asignaturas` y agregar el campo `prerrequisitos`.  
> Luego re-ejecutar la pipeline completa.

---

## 7. Fusiones Propuestas — Justificación Académica

### ABM101 + PhyOce104 → *"Batimetría Acústica y Física Oceánica"*
- **Horas actuales:** 180 + 100 = 280h → **propuesta: 240–260h**
- **IHO:** H1/H2/H6 (ABM101) + F2/Oceanografía (PhyOce104)
- **Reiteraciones:** 6 pares únicos, 1 INNECESARIA al 91% (velocidad del sonido)
- **Fundamento:** La velocidad del sonido es el nexo físico central. PhyOce104 enseña la física (propiedades del agua), ABM101 la aplica (corrección de sondajes). En paralelo Sem 1, la secuencia teoría→aplicación no puede darse.
- **Semestre propuesto:** 1

### HO202 + RS201 → *"Métodos de Levantamiento Hidrográfico"*
- **Horas actuales:** 160 + 81 = 241h → **propuesta: 200–220h**
- **IHO compartido:** H4 — Survey Operations and Applications
- **Reiteraciones:** 5 pares, 2 INNECESARIA al 100% (calibración + detección objetos = 57.6h)
- **Fundamento:** Mismo flujo de trabajo de levantamiento (planificación→calibración→adquisición→QC), sensores distintos (multihaz vs LiDAR). 38.8% del tiempo combinado es duplicación.
- **Semestre propuesto:** 2

### LSM102 + OA203 → *"Geodesia y Ajuste de Observaciones"*
- **Horas actuales:** 122 + 100 = 222h → **propuesta: 190–200h**
- **IHO compartido:** F1 — Earth Models (F1.6b Theory of observations)
- **Reiteraciones:** 5 pares, 4 INNECESARIA (80% del total — mayor densidad de los 3 pares)
- **Fundamento:** Teoría de observaciones e incertidumbre enseñada dos veces sin diferenciación.
- **Condición:** LSM102 está en Sem 1 y OA203 en Sem 2. La fusión debe resolver la ubicación semestral. Alternativa: restructuración coordinada (LSM102 retira contenidos de incertidumbre; OA203 los profundiza con referencia explícita a LSM102).
- **Semestre propuesto:** 2 (o split Sem 1-2)

---

## 8. Próximos Pasos — Por Prioridad

### Prioridad ALTA

1. **Resolver GDM301** — cerrar archivo Word, re-ejecutar `py extractor_programas.py`, luego correr la pipeline completa. GDM301 (T=54/P=100/AE=6 = 160h) es la asignatura más grande con horas prácticas y debe incluirse en la matriz de reiteración.

2. **Ingresar prerrequisitos oficiales** — confirmar con autoridades SHOA la lista de prerrequisitos, agregarlos en `analisis_progresion.py` y regenerar. Esto activa el grafo de progresión en el dashboard.

3. **Corregir niveles IHO fuera de escala** — en `analisis_progresion.py` aplicar `min(nivel, 3)` para HDP302 y LR303. Regenerar `progresion_analisis.json`.

### Prioridad MEDIA

4. **Deployar en Streamlit Cloud** — ir a `share.streamlit.io`, conectar repositorio `jsantistavilo-maker/shoa-curriculum-design`, branch `main`, entry point `app_diseno.py`. Actualizar `README.md` con la URL resultante.

5. **Normalizar puntos finales** — en `matriz_reiteracion.py` agregar `.rstrip(".")` al construir textos de contenido. Regenerar `reiteracion_matriz.json`. Reducirá el conteo de ~93 a ~80 pares reales.

6. **Verificar generar_word.py** — ejecutar `py generar_word.py` con los datos actualizados y revisar el documento Word generado antes de presentar a autoridades.

### Prioridad BAJA

7. **Logo SHOA en assets/** — ejecutar `py setup_assets.py` o colocar manualmente en `assets/logo_shoa.png`. Mejora visual del dashboard, no afecta funcionalidad.

8. **Corregir typo OA203** — en `curriculum_data.json` el nombre es "Observatiion Adjustment" (doble 'i'). Corregir manualmente si se va a presentar el JSON directamente.

---

## 9. Datos Clave de la Malla

### Horas Malla Vigente (fuente: `curriculum_data.json`)

| Asignatura | Nombre | Sem | T | P | AE | Total |
|---|---|---|---|---|---|---|
| ABM 101 | Acoustic Bathymetric Methods | 1 | 98 | 69 | 13 | **180** |
| GDM 301 | Geospatial Data Management | 3 | 54 | 100 | 6 | **160** |
| GP 204 | Geodetic Positioning | 2 | 54 | 57 | 9 | **120** |
| HDP 302 | Hydrographic Data Processing | 3 | 43 | 117 | 20 | **180** |
| HO 202 | Hydrographic Operations | 2 | 84 | 66 | 10 | **160** |
| LR 303 | Laws and Regulations | 4 | 27 | 11 | 2 | **40** |
| LSM 102 | Land Surveying Methods | 1 | 56 | 59 | 7 | **122** |
| MGG 103 | Marine Geology and Geophysics | 1 | 71 | 18 | 11 | **100** |
| OA 203 | Observation Adjustment | 2 | 47 | 50 | 3 | **100** |
| PH 401 | Proyecto Hidrográfico *(práctica)* | 4 | 0 | 534 | 208 | **742** |
| PhyOce 104 | Physical Oceanography | 1 | 51 | 45 | 4 | **100** |
| RS 201 | Remote Sensing | 2 | 44 | 35 | 2 | **81** |
| SG 304 | Satellite Geodesy | 3 | 46 | 58 | 6 | **110** |
| WTC 205 | Water Levels, Tides and Currents | 2 | 43 | 58 | 4 | **105** |
| **TOTAL** | | | | | | **2,300h** |

> RS202 (39h) y WTC202 (15h) aparecen en el Excel pero son versiones antiguas — no incluir en análisis ni propuesta.

### Resumen del Análisis

| Métrica | Valor |
|---|---|
| Asignaturas en malla vigente | 14 (+ 2 versiones antiguas RS202/WTC202) |
| Asignaturas con programa extraído correctamente | 13/14 |
| Pares de contenido similares detectados | 93 únicos |
| Pares clasificados INNECESARIA | 13 |
| Horas recuperables estimadas (INNECESARIA) | 209.4h |
| Horas totales malla sin PH401 | ~1,558h |
| Horas totales malla con PH401 | ~2,300h |
| Tópicos IHO cubiertos | F1, F2, H1, H2, H3, H4, H6, H8 |
| Tópicos IHO no cubiertos | F3, H5, H7 |

---

*Proyecto activo — SHOA / Programa de Hidrografía / Rediseño Curricular 2026*
