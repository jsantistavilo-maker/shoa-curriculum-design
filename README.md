# SHOA Curriculum Design — Análisis de Rediseño Curricular

Dashboard interactivo para el análisis y propuesta de rediseño curricular del
programa de Hidrografía del Servicio Hidrográfico y Oceanográfico de la Armada
(SHOA), basado en los estándares IHO S-5A.

## 🌐 Dashboard Online

**[Abrir Dashboard →](TU_LINK_AQUI)**

## 📊 Descripción del Proyecto

Reestructuración del programa de Hidrografía de la Armada de Chile a **1.5 años
(3 semestres)**, basada en los estándares **IHO S-5A**. Incluye:

| Tab | Contenido |
|-----|-----------|
| 🗺️ Mapa de Progresión | Grafo de dependencias y secuenciación por semestre |
| 🔁 Matriz de Reiteración | Contenidos duplicados y horas recuperables |
| 📊 Profundidad IHO | Alineación con niveles B/I/A de la norma IHO S-5A |
| 📋 Propuesta Curricular | Nueva malla — Versión A y Versión B |
| 📄 Exportar Word | Documento de propuesta descargable |
| 🔍 Validación de Datos | Contenido detallado por asignatura y unidad temática |

## 🚀 Ejecutar Localmente

```bash
pip install -r requirements.txt
streamlit run app_diseno.py
```

## 📁 Estructura del Repositorio

```
shoa-curriculum-design/
├── app_diseno.py                   # Dashboard principal
├── requirements.txt
├── .streamlit/config.toml          # Tema y configuración
├── assets/logo_shoa.png            # Logo (opcional)
├── curriculum_data.json
├── niveles_iho_norma.json
├── programas_estructurados.json
├── progresion_analisis.json
├── reiteracion_matriz.json
├── profundidad_iho.json
└── propuesta_curricular.json
```

## ⚙️ Regenerar Datos (solo ejecución local)

Los documentos fuente originales (Word, PDF, Excel) no se incluyen por
confidencialidad. Para regenerar los JSON desde documentos locales:

```bash
py extractor_programas.py
py analisis_progresion.py
py matriz_reiteracion.py
py analisis_profundidad.py
py propuesta_curricular.py
```

## 🔒 Confidencialidad

Los programas de asignaturas (Word), la norma IHO S-5A (PDF) y la planilla de
malla (Excel) son documentos institucionales del SHOA. Solo se publican los
datos procesados en JSON, sin información clasificada.

---
*Servicio Hidrográfico y Oceanográfico de la Armada de Chile (SHOA)*
