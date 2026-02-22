# Code Review - Fase 1 y Fase 2 del Sistema de Memoria

## Contexto del Proyecto

Este es un proyecto Python 3.11+ que implementa un sistema de memoria persistente usando Clean Architecture. El proyecto sigue TDD estricto con cobertura mínima del 95%.

### Stack Tecnológico
- Python 3.11+ con tipado estricto (mypy strict mode)
- Pydantic para validación de datos
- SQLite con WAL mode para persistencia
- FTS5 para búsqueda de texto completo
- dependency-injector para DI
- pytest con pytest-cov

### Arquitectura
```
src/
├── domain/           # Entidades inmutables (frozen dataclasses)
├── application/      # Casos de uso, servicios, excepciones
├── infrastructure/   # DB, config, platform-specific
└── interfaces/       # CLI, adaptadores
```

## Archivos a Revisar

### Fase 1 - Foundation (Completada)
1. `src/infrastructure/persistence/database.py` - SQLite connection con WAL mode
2. `src/infrastructure/persistence/migrations.py` - Sistema de migraciones secuenciales
3. `src/infrastructure/persistence/container.py` - DI container
4. `src/infrastructure/persistence/migrations/001_create_observations_table.sql` - Schema FTS5
5. `tests/unit/infrastructure/test_database_config.py` - Tests DB (17 tests)
6. `tests/unit/infrastructure/test_migrations.py` - Tests migraciones (15 tests)
7. `tests/unit/infrastructure/test_container.py` - Tests DI (8 tests)

### Fase 2 - MVP Memory Logic (En Progreso)
1. `src/domain/entities/observation.py` - Entidad Observation
2. `src/infrastructure/persistence/repositories/observation_repository.py` - Repository CRUD + FTS
3. `tests/unit/infrastructure/test_observation_repository.py` - Tests repository

## Criterios de Revisión

### 1. Calidad de Código
- [ ] ¿Los type hints son completos y correctos?
- [ ] ¿Las entidades son inmutables (frozen=True)?
- [ ] ¿Se usan dataclasses/pydantic correctamente?
- [ ] ¿Los imports siguen el orden correcto (stdlib -> third-party -> local)?

### 2. Arquitectura
- [ ] ¿Se respeta Clean Architecture (dependencies inward)?
- [ ] ¿El repositorio está correctamente separado?
- [ ] ¿La inyección de dependencias es correcta?

### 3. Manejo de Errores
- [ ] ¿Las excepciones personalizadas se usan correctamente?
- [ ] ¿Se preservan las excepciones originales (chaining)?
- [ ] ¿Los mensajes de error son descriptivos?

### 4. Testing
- [ ] ¿Los tests siguen el patrón AAA (Arrange-Act-Assert)?
- [ ] ¿La cobertura es >= 95%?
- [ ] ¿Los edge cases están cubiertos?

### 5. Seguridad
- [ ] ¿Se usan queries parametrizadas (no SQL injection)?
- [ ] ¿La validación de inputs es exhaustiva?

### 6. Performance
- [ ] ¿Se usan índices correctamente?
- [ ] ¿FTS5 está configurado óptimamente?
- [ ] ¿Se evitan N+1 queries?

## Formato de Salida Esperado

Entrega tu revisión en el siguiente formato:

```markdown
# Code Review Report - [Fecha]

## Resumen Ejecutivo
[Breve resumen del estado general del código]

## Issues Críticos (DEBEN ARREGLARSE)
### [Archivo] - [Línea]
- **Problema**: [Descripción]
- **Solución**: [Recomendación específica]

## Issues Menores (DEBERÍAN ARREGLARSE)
### [Archivo] - [Línea]
- **Problema**: [Descripción]
- **Solución**: [Recomendación específica]

## Sugerencias de Mejora (OPCIONALES)
### [Archivo]
- [Sugerencia]

## Puntos Positivos
- [Lo que está bien hecho]

## Cobertura de Tests
- Coverage actual: [X]%
- Líneas no cubiertas: [lista]
- Tests faltantes: [lista]

## Veredicto Final
- [ ] APROBADO - Código listo para producción
- [ ] APROBADO CON RESERVAS - Issues menores que no bloquean
- [ ] REQUIERE CAMBIOS - Issues críticos que deben arreglarse
- [ ] RECHAZADO - Problemas arquitectónicos graves
```

## Dónde Entregar Tu Trabajo

Después de completar la revisión, guarda tu reporte en:
`/home/user/fork_agent/.stash/code_reviews/review_YYYYMMDD_HHMMSS.md`

Usa el formato de nombre de archivo con la fecha y hora actual.

## Instrucciones Adicionales

1. Lee TODOS los archivos listados arriba antes de evaluar
2. Ejecuta los tests si es necesario: `uv run pytest tests/unit/infrastructure/ -v --cov=src`
3. Usa mypy para verificar tipos: `uv run mypy src/`
4. Usa ruff para linting: `uv run ruff check src/`
5. Sé específico en tus recomendaciones (incluye líneas de código)

¡Comienza la revisión ahora!
