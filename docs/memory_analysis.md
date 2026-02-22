# Plan de Proyecto v3.0 (Tech & Sec Optimized)

## [Estado de Ejecución]
- **Status:** En Progreso
- **Fase Actual:** Iniciando Fase 1 (Cimentación Técnica)
- **Cobertura de Tests:** 0% (El *tooling* está listo, pero aún no hay código de aplicación para medir).
- **Decisiones Técnicas:**
    - Se ha establecido un umbral de cobertura de pruebas del **95%** en `pyproject.toml` para garantizar la máxima calidad.
    - Se ha configurado `mypy` en modo `strict` para forzar un tipado estricto y prevenir errores de tipo en tiempo de ejecución.
    - Se ha implementado un pipeline de `pre-commit` con `ruff` y `mypy` para automatizar la validación de la calidad del código antes de cada commit, mejorando la DevEx y previniendo la deuda técnica.
    - Las dependencias de desarrollo se han añadido explícitamente a `requirements.txt` para asegurar un entorno de desarrollo consistente.

---

### **🛡️ Inyecciones Técnicas y de Seguridad Aplicadas**
*(Sin cambios)*

---

### **1. Resumen Ejecutivo y Objetivos**
*(Sin cambios)*

---

### **2. Roadmap de Alto Nivel (Re-estructurado para Calidad Primero)**

| Fase | Título | Objetivo Principal | Duración Estimada | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 0**| **Habilitación de Calidad y Seguridad** | Configurar el *tooling* estricto de calidad, testing y seguridad. | **S (Small)**: ~1 Semana | ✅ **Completado** |
| **Fase 1**| **Cimentación Técnica (Foundation)** | Establecer la infraestructura de persistencia robusta (DB Core, migraciones, DI). | **S (Small)**: ~2 Semanas | ⏳ **En Progreso** |
| **Fase 2**| **MVP: Lógica de Memoria Central** | Implementar la lógica para guardar y buscar memorias con pruebas y seguridad garantizadas. | **M (Medium)**: ~4-5 Semanas | ⬜ Pendiente |
| **Fase 3**| **Inteligencia Proactiva** | Implementar la "Capa de Sumarización" sobre una base ya probada y segura. | **M (Medium)**: ~5-6 Semanas | ⬜ Pendiente |

---

### **3. Desglose Detallado por Fases**

#### **Fase 0: Habilitación de Calidad y Seguridad**

**Épica 0.1: Configuración del Pipeline de Calidad Automatizado**
*   *Descripción:* Asegurar que cada línea de código futuro cumpla con un estándar de calidad medible y automatizado.

| Tarea Técnica | Criterios de Aceptación | Estado |
| :--- | :--- | :--- |
| **T-0.1.1: Configurar `pytest` y Cobertura.** | 1. `pytest` está configurado.<br>2. `pytest-cov` configurado con umbral del **95%**. | ✅ **Hecho** |
| **T-0.1.2: Configurar `ruff` y `mypy`.** | 1. `ruff` configurado para linting/formateo.<br>2. `mypy` configurado en modo **estricto**. | ✅ **Hecho** |
| **T-0.1.3: Implementar `pre-commit` hooks.** | 1. `.pre-commit-config.yaml` creado.<br>2. Un `git commit` falla si el código no valida. | ✅ **Hecho** |

#### **Fase 1: Cimentación Técnica (Foundation)**

**Épica 1.1: Configuración del Núcleo de la Base de Datos**
*   *Descripción:* Preparar el proyecto para una interacción robusta, segura y a prueba de futuro con SQLite.

| Tarea Técnica | Criterios de Aceptación | Estado |
| :--- | :--- | :--- |
| **T-1.1.1: Conexión a SQLite y manejo de rutas.** | 1. La ruta a la BBDD se gestiona con `pathlib.Path`.<br>2. Conexión en modo **WAL** y con `busy_timeout`. | ⬜ **Pendiente** |
| **T-1.1.2: Sistema de migraciones y DI.** | 1. Script simple para migraciones secuenciales de SQL.<br>2. Contenedor de **Inyección de Dependencias** establecido. | ⬜ **Pendiente** |
| **T-1.1.3: Definición de Excepciones Personalizadas.**| 1. Módulo `src/application/exceptions.py` creado.<br>2. Excepciones `RepositoryError`, `ServiceError` definidas. | ⬜ **Pendiente** |

*(El resto del plan permanece sin cambios)*.
