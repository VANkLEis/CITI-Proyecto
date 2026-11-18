"""Genera las fuentes PlantUML y los PNG de los 9 diagramas de arquitectura CITI.

Uso:
  <venv-docs>/python.exe docs/sustentacion/scripts/gen_diagrams.py

Requiere Java y plantuml.jar (ruta configurable con PLANTUML_JAR).
No modifica el cÃ³digo de la aplicaciÃ³n.
"""
from __future__ import annotations

import os
import subprocess
from puml_clean import clean
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "sustentacion"
FUENTES = BASE / "fuentes"
SALIDA = BASE / "diagramas"
JAR = Path(os.environ.get("PLANTUML_JAR", r"C:\Users\Santiago\AppData\Local\Temp\opencode\plantuml.jar"))
TARGET_W = 2200
MIN_H = 1080

FUENTES.mkdir(parents=True, exist_ok=True)
SALIDA.mkdir(parents=True, exist_ok=True)

COMMON = r"""
skinparam backgroundColor #FFFFFF
skinparam shadowing false
skinparam defaultFontName "Segoe UI"
skinparam defaultFontSize 18
skinparam dpi 220
skinparam ArrowColor #5F6B7A
skinparam ArrowThickness 1.4
skinparam actorBackgroundColor #E8F6FA
skinparam actorBorderColor #00ACC9
skinparam actorFontColor #132740
skinparam rectangleBackgroundColor #F7FAFC
skinparam rectangleBorderColor #00ACC9
skinparam rectangleFontColor #132740
skinparam componentBackgroundColor #F7FAFC
skinparam componentBorderColor #00ACC9
skinparam componentFontColor #132740
skinparam databaseBackgroundColor #E8F6FA
skinparam databaseBorderColor #132740
skinparam databaseFontColor #132740
skinparam nodeBackgroundColor #F7FAFC
skinparam nodeBorderColor #80BA27
skinparam packageBackgroundColor #FFFFFF
skinparam packageBorderColor #DDE3EA
skinparam noteBackgroundColor #FFF8E1
skinparam noteBorderColor #D99A00
skinparam noteFontColor #5F4A00
skinparam classBackgroundColor #F7FAFC
skinparam classBorderColor #132740
skinparam classFontColor #132740
skinparam classFontSize 14
skinparam stateBackgroundColor #F7FAFC
skinparam stateBorderColor #00ACC9
skinparam stateFontColor #132740
skinparam sequenceParticipantBackgroundColor #F7FAFC
skinparam sequenceParticipantBorderColor #00ACC9
skinparam sequenceLifeLineBorderColor #B8C4D0
skinparam sequenceArrowColor #5F6B7A
"""

DIAGRAMS: dict[str, str] = {}

DIAGRAMS["01_contexto_c4.puml"] = r"""
@startuml
title <b>CITI Â· Contexto C4 (Nivel 1)</b>\nActores, frontera del sistema y sistemas externos
left to right direction
""" + COMMON + r"""
actor "Cliente / Empresa" as cliente
actor "Estudiante\n(consultor / tutor)" as estudiante
actor "Docente asesor" as docente
actor "Coordinador\nde Ã¡rea" as coordinador
actor "Director CITI" as director

rectangle "Sistema CITI\nConsultorio de IngenierÃ­a, TecnologÃ­a e InnovaciÃ³n\nUCC Campus IbaguÃ©â€“El Espinal" as citi {
  rectangle "Landing pÃºblica\ny registro de empresa" as landing
  rectangle "Portales por rol\nCliente Â· Estudiante Â· Docente\nCoordinador Â· Director" as portales
  rectangle "Agenda y solicitudes\nfranjas Â· reservas Â· estados" as agenda
  rectangle "Trazabilidad y mÃ©tricas\nCitaEvento Â· indicadores Â· CSV" as traza
  rectangle "AdministraciÃ³n\nDjango Admin" as admin
}

node "Navegador web\nHTML Â· CSS Â· JavaScript" as browser
cloud "CDN FullCalendar\n(calendario del cliente)" as cdn
node "Servidor WSGI\nDjango 5.x" as wsgi
database "Base de datos\nSQLite (dev) / PostgreSQL (prod)" as db
folder "MEDIA_ROOT\nAdjuntos de solicitudes" as media
cloud "GitHub\norigin/main" as github

cliente --> landing : registra empresa / inicia sesiÃ³n
cliente --> portales : solicita, sigue y aprueba
estudiante --> portales : registra bitÃ¡cora
docente --> portales : gestiona casos y entregables
coordinador --> portales : revisa y asigna
director --> portales : consulta indicadores globales
director --> admin : administra registros
browser --> landing : HTTP
browser --> portales : HTTP
landing --> wsgi
portales --> wsgi
agenda --> db : persiste y consulta
traza --> db : eventos e indicadores
wsgi --> media : adjuntos autorizados
portales --> cdn : calendario
github --> wsgi : despliegue

note bottom of citi
  La frontera del sistema agrupa la aplicaciÃ³n Django.
  Los actores solo acceden a travÃ©s de HTTP y reglas de rol.
end note
@enduml
"""

DIAGRAMS["02_casos_uso.puml"] = r"""
@startuml
title <b>CITI Â· Casos de uso reales</b>\nCinco roles vigentes y sus interacciones principales
left to right direction
""" + COMMON + r"""
actor "Cliente / Empresa" as cliente
actor "Estudiante\n(consultor / tutor)" as estudiante
actor "Docente asesor" as docente
actor "Coordinador\nde Ã¡rea" as coordinador
actor "Director CITI" as director

rectangle "Sistema CITI" {
  usecase "UC-01\nRegistrarse / iniciar sesiÃ³n" as uc01
  usecase "UC-02\nSolicitar asesorÃ­a o consultorÃ­a" as uc02
  usecase "UC-03\nConsultar mis solicitudes\ny seguimiento" as uc03
  usecase "UC-04\nComentar / solicitar ajuste" as uc04
  usecase "UC-05\nAprobar o rechazar entregable" as uc05
  usecase "UC-06\nCancelar solicitud" as uc06
  usecase "UC-07\nRegistrar bitÃ¡cora de apoyo" as uc07
  usecase "UC-08\nConsultar casos de apoyo" as uc08
  usecase "UC-09\nGestionar caso y publicar entregable" as uc09
  usecase "UC-10\nEmitir acta de cierre" as uc10
  usecase "UC-11\nRevisar bandeja y asignar\nresponsables" as uc11
  usecase "UC-12\nSeguimiento e interacciones\nde su Ã¡rea" as uc12
  usecase "UC-13\nConsultar trazabilidad\ny exportar CSV" as uc13
  usecase "UC-14\nPanel ejecutivo e indicadores" as uc14
  usecase "UC-15\nAdministrar registros" as uc15
}

cliente --> uc01
cliente --> uc02
cliente --> uc03
cliente --> uc04
cliente --> uc05
cliente --> uc06
estudiante --> uc07
estudiante --> uc08
docente --> uc09
docente --> uc10
coordinador --> uc11
coordinador --> uc12
coordinador --> uc13
director --> uc13
director --> uc14
director --> uc15

note bottom of uc13
  El coordinador ve solo su Ã¡rea;
  el director tiene alcance global.
end note
@enduml
"""

DIAGRAMS["03_componentes.puml"] = r"""
@startuml
title <b>CITI Â· Componentes C4 (Nivel 2/3)</b>\nAplicaciones, servicios de dominio e infraestructura
top to bottom direction
""" + COMMON + r"""
package "config" {
  [settings.py\nentornos Â· DB Â· media] as settings
  [urls.py\nenrutamiento raÃ­z] as urls
  [wsgi.py\npunto de entrada] as wsgi
}

package "accounts" {
  [CustomUser\nemail Â· rol Â· Ã¡rea Â· empresa] as user
  [Empresa\nrazÃ³n social Â· NIT] as empresa
  [PerfilEstudiante\nsemestre Â· crÃ©ditos Â· promedio] as perfil
  [signals.py\npromociÃ³n/degradaciÃ³n de tutor] as signals
}

package "scheduling" {
  [FranjaHoraria Â· CitaAsesoria\nagenda y estados] as citas
  [trazabilidad.py\neventos y transiciones] as traza
  [CitaEvento Â· CitaInteraccion\nauditorÃ­a e interacciÃ³n] as eventos
  [subespecialidades.py\ncatÃ¡logo de servicios] as subesp
}

package "portal" {
  [views.py\nlanding Â· dashboards Â· seguimiento] as views
  [forms.py\nautenticaciÃ³n Â· gestiÃ³n] as forms
  [indicadores.py\nmÃ©tricas y CSV] as indicadores
  [decorators.py Â· role_routing.py\ncontrol de acceso] as access
}

component "Django Admin\npersonalizado" as admin
component "Templates Django\n31 plantillas + CSS" as templates
database "ORM\nDjango" as orm
database "Base de datos\nSQLite / PostgreSQL" as db
folder "MEDIA_ROOT\nadjuntos" as media

urls --> views
wsgi --> urls
views --> forms
views --> access
views --> traza
views --> indicadores
views --> citas
views --> templates
views --> admin
forms --> user
traza --> citas
traza --> eventos
indicadores --> citas
indicadores --> eventos
citas --> subesp
citas --> orm
user --> orm
empresa --> orm
perfil --> orm
eventos --> orm
orm --> db
citas --> media
admin --> orm
signals --> perfil
signals --> user

note bottom of orm
  Las apps no acceden a la base directamente:
  todo pasa por el ORM y por los servicios de dominio.
end note
@enduml
"""

DIAGRAMS["04_capas.puml"] = r"""
@startuml
title <b>CITI · Arquitectura lógica por capas (MVT + servicios)</b>\nRecorrido de una petición HTTP
left to right direction
""" + COMMON + r"""
rectangle "1. Navegador\nHTML · CSS · JS" as n1 #E8F6FA
rectangle "2. URLconf\nconfig/urls.py" as n2 #E8F6FA
rectangle "3. Middleware + Auth\nsesión · CSRF · roles" as n3 #FFF8E1
rectangle "4. Vista FBV\nportal/views.py" as n4 #E8F6FA
rectangle "5. Servicio de dominio\ntrazabilidad.py · indicadores.py" as n5 #FFF8E1
rectangle "6. Modelo y reglas\naccounts · scheduling" as n6 #F1F8E6
rectangle "7. ORM\nDjango ORM" as n7 #EEF2F7
database "8. Base de datos\nSQLite / PostgreSQL" as n8 #EEF2F7
rectangle "Template\nDjango HTML" as tpl #E8F6FA

n1 --> n2 : HTTP
n2 --> n3 : ruta
n3 --> n4 : usuario autorizado
n4 --> n5 : llama servicio
n5 --> n6 : aplica regla
n6 --> n7 : persiste
n7 --> n8 : SQL
n4 --> tpl : renderiza
note bottom of tpl : Respuesta HTML al navegador.

legend bottom
  <b>Capas</b>
  Presentación: navegador, URLconf, vista y template.
  Aplicación: middleware/auth y servicios de dominio.
  Dominio: modelos y reglas de negocio.
  Infraestructura: ORM y base de datos.
endlegend

note bottom of n5
  Recorrido: URL -> Middleware/Auth -> View -> Service -> ORM -> DB -> Template.
  Las reglas críticas (estados, permisos, cupos) no viven en el template.
end note
@enduml
"""

DIAGRAMS["05_secuencia_reserva.puml"] = r"""
@startuml
title <b>CITI Â· Secuencia de reserva concurrente</b>\nTransacciÃ³n, bloqueo y control de cupo
autonumber
""" + COMMON + r"""
actor "Cliente" as cliente
participant "Navegador" as nav
participant "API\n/agenda/api/reservar/" as api
participant "FranjaHoraria" as franja
participant "CitaAsesoria" as cita
participant "CitaEvento" as evento
database "Base de datos" as db

cliente -> nav : elige franja y envÃ­a formulario
nav -> api : POST multipart/form-data\n(franja_id, subespecialidad, tipo, archivo)
api -> db : BEGIN Â· transaction.atomic()
api -> franja : select_for_update().get(activa=True)
franja --> api : franja bloqueada (PostgreSQL)
api -> cita : validar cupo y duplicado del cliente
alt sin cupo / duplicado / franja invÃ¡lida
  api --> nav : 409 Conflict\n{ok:false, error}
else reserva vÃ¡lida
  api -> cita : save()\nUniqueConstraint (franja, cliente)
  api -> evento : registrar_evento(creada)
  opt archivo adjunto
    api -> evento : registrar_evento(archivo_adjunto)
  end
  api -> db : COMMIT
  api --> nav : 200 OK\n{ok:true, cita_id}
end

note over franja : select_for_update es efectivo en PostgreSQL.\nEn SQLite no hay bloqueo de fila; la restricciÃ³n Ãºnica y la transacciÃ³n siguen evitando duplicados.
@enduml
"""

DIAGRAMS["06_secuencia_trazabilidad.puml"] = r"""
@startuml
title <b>CITI Â· Secuencia de trazabilidad e interacciÃ³n</b>\nAsignaciÃ³n â†’ entrega â†’ decisiÃ³n del cliente
autonumber
""" + COMMON + r"""
actor "Coordinador" as coord
actor "Docente" as docente
actor "Cliente" as cliente
participant "Portal\nvista / formulario" as portal
participant "trazabilidad.py" as traza
participant "CitaAsesoria" as cita
participant "CitaEvento" as evento
participant "CitaInteraccion" as inter
database "Base de datos" as db

group AsignaciÃ³n
  coord -> portal : abre bandeja y asigna docente/tutor
  portal -> traza : asignar_cita(cita, docente, tutor)
  traza -> cita : estado = ASIGNADA + marcas
  traza -> evento : docente_asignado Â· tutor_asignado Â· asignada
  traza -> db : COMMIT
end

group Entrega del docente
  docente -> portal : publica entregable
  portal -> traza : publicar_entrega(cita, tÃ­tulo, contenido, ficha)
  traza -> inter : ENTREGA_RESULTADOS (para_cliente=True)
  traza -> evento : entrega_publicada
  traza -> db : COMMIT
end

group DecisiÃ³n del cliente
  cliente -> portal : aprueba o solicita ajustes
  portal -> traza : registrar_decision_cliente(cita, aprobar)
  alt aprueba
    traza -> inter : APROBACION
    traza -> evento : decision_cliente
  else solicita ajustes
    opt cita finalizada
      traza -> cita : finalizada -> en_proceso (reapertura)
      traza -> evento : estado_cambiado
    end
    traza -> inter : RECHAZO_AJUSTE
    traza -> evento : decision_cliente
  end
  traza -> db : COMMIT
end

note over evento : CitaEvento es append-only: no se edita ni se borra.\nCada mutaciÃ³n y su evento comparten la misma transacciÃ³n.
@enduml
"""

DIAGRAMS["07_estados.puml"] = r"""
@startuml
title <b>CITI Â· MÃ¡quina de estados de una solicitud</b>\nTransiciones formales implementadas
""" + COMMON + r"""
state "Solicitada" as solicitada
state "Asignada" as asignada
state "En proceso" as en_proceso
state "Finalizada" as finalizada
state "Cancelada" as cancelada

[*] --> solicitada : cliente reserva
solicitada --> asignada : coordinador asigna docente/tutor
solicitada --> cancelada : cliente cancela
asignada --> en_proceso : docente inicia
asignada --> finalizada : cierre directo permitido
asignada --> cancelada : cliente / coordinaciÃ³n
en_proceso --> finalizada : docente cierra con resumen
en_proceso --> cancelada : cancelaciÃ³n
finalizada --> en_proceso : ajuste solicitado por el cliente
finalizada --> [*]
cancelada --> [*]

note right of asignada
  Una consultorÃ­a especializada
  requiere docente responsable (I-6).
end note
note right of finalizada
  La aprobaciÃ³n del cliente NO finaliza.
  El cierre administrativo lo hace el docente.
end note
note bottom of cancelada
  Cancelada es terminal.
  No hay retrocesos manuales del equipo.
end note
@enduml
"""

DIAGRAMS["08_er_real.puml"] = r"""
@startuml
title <b>CITI Â· Modelo Entidad-RelaciÃ³n real</b>\n8 modelos implementados (Django ORM)
top to bottom direction
""" + COMMON + r"""
hide circle
skinparam linetype ortho
skinparam nodesep 28
skinparam ranksep 34

class Empresa {
  id : BigAutoField <<PK>>
  razon_social : CharField
  nit : CharField
  direccion : CharField
  telefono : CharField
  sector : CharField
}

class CustomUser {
  id : BigAutoField <<PK>>
  email : EmailField <<UK>>
  password : CharField
  role : director | coordinador | docente | estudiante | cliente
  area : sistemas | civil | mixto
  student_type : consultor | tutor
  empresa_id : FK Empresa
  is_staff : BooleanField
}

class PerfilEstudiante {
  id : BigAutoField <<PK>>
  usuario_id : OneToOne CustomUser
  semestre : PositiveInteger
  creditos_aprobados : PositiveInteger
  promedio_general : Decimal
  autorizado_como_tutor : Boolean
}

class FranjaHoraria {
  id : BigAutoField <<PK>>
  inicio : DateTime
  fin : DateTime
  area : sistemas | civil | mixto
  capacidad : PositiveSmallInteger
  activa : Boolean
  creada_por_id : FK CustomUser
}

class CitaAsesoria {
  id : BigAutoField <<PK>>
  franja_id : FK FranjaHoraria
  cliente_id : FK CustomUser
  asunto : CharField
  subespecialidad : CharField
  tipo_servicio : orientacion | especializada
  estado : solicitada | asignada | en_proceso | finalizada | cancelada
  docente_asignado_id : FK CustomUser
  estudiante_apoyo_id : FK CustomUser
  archivo_adjunto : FileField
  resumen_cierre : TextField
  asignada_en : DateTime
  cerrada_en : DateTime
  calificacion : PositiveSmallInteger
}

class NotaBitacora {
  id : BigAutoField <<PK>>
  cita_id : FK CitaAsesoria
  autor_id : FK CustomUser
  texto : TextField
  creada_en : DateTime
}

class CitaEvento {
  id : BigAutoField <<PK>>
  cita_id : FK CitaAsesoria
  usuario_id : FK CustomUser
  actor_label : CharField
  tipo : CharField
  estado_anterior : CharField
  estado_nuevo : CharField
  descripcion : TextField
  metadata : JSONField
  fecha : DateTime
}

class CitaInteraccion {
  id : BigAutoField <<PK>>
  cita_id : FK CitaAsesoria
  autor_id : FK CustomUser
  rol_autor : CharField
  tipo : general | observacion | respuesta | nota_interna | ajuste | entrega | aprobacion | rechazo
  texto : TextField
  datos_extra : JSONField
  para_cliente : Boolean
  fecha : DateTime
}

Empresa "1" -- "0..*" CustomUser : emplea
CustomUser "1" -- "0..1" PerfilEstudiante : perfil acadÃ©mico
FranjaHoraria "1" -- "0..*" CitaAsesoria : agenda
CustomUser "1" -- "0..*" CitaAsesoria : solicita
CustomUser "0..1" -- "0..*" CitaAsesoria : docente
CustomUser "0..1" -- "0..*" CitaAsesoria : tutor
CitaAsesoria "1" -- "0..*" NotaBitacora : notas
CitaAsesoria "1" -- "0..*" CitaEvento : eventos
CitaAsesoria "1" -- "0..*" CitaInteraccion : interacciones
CustomUser "1" -- "0..*" CitaEvento : actor
CustomUser "1" -- "0..*" CitaInteraccion : autor

note right of CitaAsesoria
  UniqueConstraint parcial:
  (franja, cliente) para estados activos.
end note
note bottom of CitaEvento
  Registro append-only; sin update/delete desde el portal.
end note
@enduml
"""

DIAGRAMS["09_despliegue.puml"] = r"""
@startuml
title <b>CITI Â· Arquitectura de despliegue</b>\nDesarrollo local vs. producciÃ³n
left to right direction
""" + COMMON + r"""
package "Entorno desarrollo (local)" {
  node "Windows\nNavegador" as devbrowser
  node "runserver\nWSGI de desarrollo" as devserver
  database "SQLite\ndb.sqlite3" as devdb
  folder "MEDIA_ROOT\nlocal" as devmedia
  devbrowser --> devserver : HTTP :8000
  devserver --> devdb : ORM
  devserver --> devmedia : adjuntos
}

package "Entorno producciÃ³n" {
  cloud "GitHub\norigin/main" as github
  node "Nginx\nHTTPS Â· reverse proxy" as nginx
  node "Gunicorn / uWSGI\nworkers WSGI" as gunicorn
  node "Django 5\nconfig.wsgi" as django
  database "PostgreSQL\nDATABASE_URL" as pg
  folder "MEDIA_ROOT\nvolumen / S3 futuro" as media
  node "Variables de entorno\nDJANGO_ENV=produccion" as env
  node "Navegador\nHTTPS" as prodbrowser
  prodbrowser --> nginx
  nginx --> gunicorn
  gunicorn --> django
  django --> pg
  django --> media
  env --> django
  github --> nginx : despliegue
}

note bottom of django
  ColecciÃ³n de estÃ¡ticos con collectstatic.
  HTTPS, HSTS, cookies seguras y ALLOWED_HOSTS.
end note
note bottom of pg
  Postgres es la opciÃ³n recomendada para
  concurrencia y bloqueo select_for_update.
end note
@enduml
"""


def render(name: str, source: str) -> None:
    puml = FUENTES / name
    puml.write_text(clean(source.strip()) + "\n", encoding="utf-8")
    subprocess.run(
        [
            "java", "-Dfile.encoding=UTF-8", "-DPLANTUML_LIMIT_SIZE=16384", "-jar", str(JAR),
            "-charset", "UTF-8", "-tpng", "-o", str(SALIDA), str(puml),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    png = SALIDA / (puml.stem + ".png")
    if not png.exists():
        raise RuntimeError(f"PlantUML no generÃ³ {png}")
    with Image.open(png) as im:
        im = im.convert("RGB")
        # Lienzo blanco y escala mÃ­nima 2200 px de ancho / 1080 px de alto.
        scale = max(TARGET_W / im.width, MIN_H / im.height, 1.0)
        if scale > 1.0:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        canvas = Image.new("RGB", (max(im.width + 80, TARGET_W), max(im.height + 80, MIN_H)), "white")
        canvas.paste(im, ((canvas.width - im.width) // 2, (canvas.height - im.height) // 2))
        canvas.save(png, "PNG", optimize=True)
        print(f"{png.name}: {canvas.width}x{canvas.height} ({png.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    for filename, content in DIAGRAMS.items():
        if filename == "02_casos_uso.puml":
            # El diagrama 02 se compone en 5 paneles con gen_use_cases.py.
            continue
        render(filename, content)

