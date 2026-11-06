# CITI — Diagrama Entidad-Relación (Mermaid)

> Consultorio de Ingeniería, Tecnología e Innovación · UCC · 2026
> Fuente: `app/js/data.js`, `app/js/auth.js`, `app/js/dashboard.js`, `docs/documentacion-arquitectura.html §5`, `plantillas/`, `dashboards/`
> Cómo verlo: pégalo en https://mermaid.live · GitHub lo renderiza solo · VS Code con extensión Mermaid · Notion / Obsidian bloque ```mermaid

```mermaid
erDiagram
    USUARIO {
        string id_usuario PK
        string email UK
        string password_hash
        string nombre_completo
        string rol "director-coordinador-docente-estudiante-cliente"
        string tipo_estudiante "consultor-tutor-NULL"
        string area "sistemas-civil-NULL"
        string id_empresa FK "solo cliente"
        boolean activo
    }
    EMPRESA {
        string id_empresa PK
        string razon_social
        string nit UK
        string direccion
        string telefono
        string sector_economico
        string nombre_gerente
    }
    SOLICITUD {
        string id_solicitud PK
        string id_empresa FK
        string id_cliente FK
        string tipo "asesoria-taller-practica-convenio-exploracion"
        string area "sistemas-civil-mixto"
        string descripcion
        string estado "pendiente-aprobado-rechazado-en_proceso-completado-cerrado"
        string fecha_solicitud
        string id_coordinador_aprueba FK
        string observacion_rechazo
    }
    ASIGNACION {
        string id_asignacion PK
        string id_solicitud FK_UK "UNIQUE 1-1"
        string id_tutor FK
        string id_docente FK
        string fecha_asignacion
    }
    INFORME {
        string id_informe PK
        string id_solicitud FK
        string id_tutor FK
        string tipo "parcial-final"
        string contenido
        string ruta_pdf
        string estado "borrador-enviado-en_revision-aprobado-devuelto"
        string fecha_envio
        string id_docente_revisor FK
    }
    FIRMA {
        string id_firma PK
        string id_informe FK_UK "UNIQUE 1-1 final"
        string id_usuario FK
        string fecha_firma
    }
    CONSULTA {
        string id_consulta PK
        string fecha
        string razon_social
        string direccion_telefono
        string sector_economico
        string area
        string descripcion
        string id_consultor FK
        string estado
    }
    CORRESPONDENCIA {
        string id_correspondencia PK
        string tipo "entrada-salida"
        string fecha
        string asunto
        string id_consultor FK
    }
    TALLER {
        string id_taller PK
        string tema
        string objetivo
        string fecha
        string id_docente FK
        string id_empresa FK
        int num_asistentes
    }
    PRACTICA {
        string id_practica PK
        string id_solicitud FK
        string id_estudiante FK
        string id_docente FK
        string id_empresa FK
        string estado "activa-evaluada-cerrada"
        float evaluacion
    }
    VISITA_EMPRESARIAL {
        string id_visita PK
        string id_coordinador FK
        string id_empresa FK
        string fecha
        string diagnostico
    }
    CONVENIO {
        string id_convenio PK
        string id_empresa_aliada FK
        string objeto
        string vigencia_inicio
        string vigencia_fin
    }
    BOLSA_EMPLEO {
        string id_oferta PK
        string id_empresa FK
        string vacante
        string requisitos
        string fecha_publicacion
        string id_consultor_gestor FK
    }
    PROGRAMA_RADIAL {
        string id_programa PK
        string tema
        string fecha_emision
        string id_consultor FK
    }

    EMPRESA ||--o{ USUARIO : "tiene clientes"
    EMPRESA ||--o{ SOLICITUD : "genera"
    USUARIO ||--o{ SOLICITUD : "crea cliente CU-01"
    USUARIO ||--o{ SOLICITUD : "aprueba coordinador CU-07"
    SOLICITUD ||--|| ASIGNACION : "tiene CU-08"
    ASIGNACION }o--|| USUARIO : "tutor asignado"
    ASIGNACION }o--|| USUARIO : "docente asignado"
    SOLICITUD ||--o{ INFORME : "genera CU-12"
    INFORME }o--|| USUARIO : "revisa docente CU-13"
    INFORME ||--|| FIRMA : "requiere CU-03"
    FIRMA }o--|| USUARIO : "firma cliente"
    USUARIO ||--o{ CONSULTA : "registra consultor CU-04"
    USUARIO ||--o{ CORRESPONDENCIA : "gestiona CU-05"
    USUARIO ||--o{ TALLER : "imparte docente CU-14"
    EMPRESA ||--o{ TALLER : "recibe"
    SOLICITUD ||--|| PRACTICA : "origina CU-15"
    USUARIO ||--o{ VISITA_EMPRESARIAL : "registra coordinador CU-09"
    EMPRESA ||--o{ VISITA_EMPRESARIAL : "recibe"
    EMPRESA ||--o{ CONVENIO : "suscribe aliada"
    EMPRESA ||--o{ BOLSA_EMPLEO : "publica CU-06"
    USUARIO ||--o{ PROGRAMA_RADIAL : "conduce CU-06"
```

## Cobertura por módulo

| Entidad | Origen en el proyecto | CU |
|---|---|---|
| USUARIO | `app/js/data.js users` + `auth.js SESSION_KEY, role, studentType, area, empresaId` | CU-20, CU-21, CU-16 |
| EMPRESA | `data.js solicitudes[].empresaId` + banco empresas director | CU-01 |
| SOLICITUD | `data.js solicitudes[]` + flujo cliente→coordinador | CU-01, CU-07, CU-02 |
| ASIGNACION | `solicitudes[].tutor, docente` + `dashboard.js asignaciones` | CU-08 |
| INFORME | `dashboard.js informes` + `plantillas/informe-asesoria.html` | CU-12, CU-13 |
| FIRMA | firma representante legal en `informe-asesoria.html` | CU-03 |
| CONSULTA | `data.js consultas[]` + `plantillas/registro-consultas.html` | CU-04 |
| CORRESPONDENCIA | menú `correspondencia` estudiante consultor | CU-05 |
| TALLER | menú `talleres` docente | CU-14 |
| PRACTICA | menú `practicas` docente | CU-15 |
| VISITA_EMPRESARIAL | menú `visitas` coordinador | CU-09 |
| CONVENIO | driver empresas aliadas + tipo solicitud `convenio` | — |
| BOLSA_EMPLEO | menú `empleo` consultor | CU-06 |
| PROGRAMA_RADIAL | menú `radial` todos los estudiantes | CU-06 |

## Workflow (State Machine)

`pendiente → aprobado → en_proceso → completado → cerrado` (`rechazado` rama de CU-07).
`INFORME: borrador → enviado → en_revision → aprobado | devuelto`.

## ENUMs

- `USUARIO.rol`: `director, coordinador, docente, estudiante, cliente`
- `USUARIO.tipo_estudiante`: `consultor (8°+), tutor (3°+), NULL`
- `SOLICITUD.area / USUARIO.area`: `sistemas, civil, mixto`
