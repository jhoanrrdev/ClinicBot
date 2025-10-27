# 00_Alcance_Tecnico_ClinicBot

## 1. Descripción general
ClinicBot es un asistente para clínicas que facilita la atención al paciente mediante respuestas automáticas,
agenda básica y panel de administración.

### Objetivo general
Implementar un PMV funcional que permita responder preguntas frecuentes, gestionar citas básicas y disponer
de un panel mínimo para seguimiento.

### Objetivos específicos (ejemplo)
1. Integrar un endpoint de salud y un módulo de autenticación mínimo.
2. Diseñar una interfaz React para mostrar estado del sistema y agenda simple.
3. Desplegar backend y frontend en entornos de pruebas públicos (staging).
4. Documentar instalación, despliegue y roles.

## 2. Alcance del PMV
**Incluye:**
- Respuestas automáticas básicas (FAQ).
- Agenda simple (crear/listar/eliminar citas).
- Panel básico de administración (estado del sistema).

**Excluye (por ahora):**
- Pagos en línea.
- Historias clínicas completas.
- Integraciones avanzadas con ERP.

## 3. Stack tecnológico
- **Backend:** FastAPI (Python)
- **Frontend:** React + Vite
- **Base de datos:** PostgreSQL (producción), SQLite (desarrollo local)
- **Integraciones (posterior):** WhatsApp API (Twilio/Meta Cloud)
- **Herramientas:** GitHub, Postman, Draw.io/Lucidchart, Kanban (GitHub Projects/Trello/Jira)

## 4. Roles
- Líder técnico
- Backend
- Frontend
- DevOps
- QA

## 5. Guía de instalación (resumen)
Ver README en la raíz del repositorio para pasos detallados de backend y frontend.

## 6. Evidencias
Colocar capturas de ejecución local y URLs de staging en `docs/evidencias/`.
