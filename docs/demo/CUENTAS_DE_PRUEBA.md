# Cuentas de prueba — CITI (solo entorno local de desarrollo)

Credenciales de **demostración académica local** creadas por
`manage.py seed_demo`. **No usar en despliegues reales**; si el sistema se
exposa fuera del portátil, cambiar o desactivar estas cuentas (ver
`VARIABLES_ENTORNO.md`).

Contraseña única (sobrepornible con `CITI_DEMO_PASSWORD`):

```
CITIPass2026*
```

## Cuentas y portales

| Rol | Correo | Portal de acceso | Notas |
|---|---|---|---|
| Director CITI | `director@citi.ucc.edu.co` | `/cuenta/login/?rol=director` | Ricardo Pérez. `is_staff` + permisos de dominio (accounts/scheduling) concedidos por el seed, **sin** superusuario: entra a `/admin/` con la misma cuenta |
| Coordinador Sistemas | `coordinador@citi.ucc.edu.co` | `?rol=coordinador` | Bandeja del área Sistemas |
| Coordinador Civil | `coordinador.civil@citi.ucc.edu.co` | `?rol=coordinador` | Bandeja del área Civil (mismo portal, distinta área) |
| Docente Sistemas | `docente@citi.ucc.edu.co` | `?rol=docente` | Ve solo sus casos asignados |
| Docente Civil | `docente.civil@citi.ucc.edu.co` | `?rol=docente` | Idem |
| Estudiante tutora (Sistemas) | `estudiante@citi.ucc.edu.co` | `?rol=estudiante` | Perfil real: 9° semestre, 150 créditos, promedio 4,50 → promotora a tutora automática |
| Estudiante tutor (Civil) | `estudiante.civil@citi.ucc.edu.co` | `?rol=estudiante` | Perfil: 10° semestre, 168 créditos, promedio 4,30 |
| Cliente / Empresa | `cliente@empresatolima.co` | `?rol=cliente` | Empresa: *Empresa Tolima Demo* NIT 900123456. Dueño de todas las solicitudes del set demo |

Cuentas adicionales de registro público (para probar login/registro):

| Correo | Rol | Origen |
|---|---|---|
| `carlos.ramirez@empresatolima.co` | cliente | creación manual previa (contraseña propia, no documentada aquí). Sus 4 solicitudes históricas quedaron archivadas como `cancelada` con nota de trazabilidad |
| `coord.civil@citi.ucc.edu.co` | coordinador civil | creación manual previa, duplicado funcional de `coordinador.civil@…` (convivencia inofensiva; se puede retirar en una fase posterior) |
| Usuario adicional | director + `is_staff` | cuenta personal creada manualmente antes del seed (no documentada aquí). El seed no la toca; la demo usa `director@citi.ucc.edu.co` |

## Cómo se usa en la demo

1. Abrir la landing → "Iniciar sesión".
2. Seleccionar el **portal del rol** (lista izquierda) — si se omite, el login
   lo exige ("Seleccione un portal de acceso…").
3. Ingresar correo + contraseña única.
4. El sistema redirige automáticamente al dashboard del rol correcto.

Seguridad de roles verificada (Fase 02):
- Un usuario de otro rol **no puede** abrir portales ajenos: se redirige al
  propio sin fuga de datos (regresión SEG-01 cubierta por `test_matriz_rol_x_portal`).
- La cuenta de estudiante **no aparece** como tutor en asignación si su perfil
  no supera los umbrales (8° / 130 créditos / 4.0): la elegibilidad la fija
  el perfil académico, no el rol.

## Notas

- El registro público (`/cuenta/registro/`) solo crea clientes y hoy **valida
  la contraseña** (mínimo 8, no común, no numérica, similitud) — B-5/SEG-13.
- El login revela el portal real de una cuenta cuando el `expected_role` no
  coincide; es conveniencia de aula, pero se documenta como riesgo (SEG-14).
