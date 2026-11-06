/**
 * CITI — Datos del sistema (demo)
 * 5 roles operativos según documento CITI:
 * Director · Coordinador · Docente · Estudiante · Cliente
 */
const CITI_DATA = {
  roles: {
    director: {
      id: 'director',
      label: 'Director CITI',
      portal: 'Gobernanza del consultorio',
      color: '#132740',
      dashboard: 'dashboards/director.html',
    },
    coordinador: {
      id: 'coordinador',
      label: 'Coordinador de área',
      portal: 'Sistemas o Civil',
      color: '#00a0c6',
      dashboard: 'dashboards/coordinador.html',
    },
    docente: {
      id: 'docente',
      label: 'Docente asesor',
      portal: 'Supervisión académica',
      color: '#1a6b8a',
      dashboard: 'dashboards/docente.html',
    },
    estudiante: {
      id: 'estudiante',
      label: 'Estudiante',
      portal: 'Recepción o tutoría',
      color: '#80ba27',
      dashboard: 'dashboards/estudiante.html',
    },
    cliente: {
      id: 'cliente',
      label: 'Cliente / Empresa',
      portal: 'Empresas e instituciones',
      color: '#5f5e5e',
      dashboard: 'dashboards/cliente.html',
    },
  },

  /** Tipos de estudiante (funciones distintas, mismo portal) */
  studentTypes: {
    consultor: { label: 'Consultor de recepción', minSemestre: 8 },
    tutor: { label: 'Tutor de casos', minSemestre: 3 },
  },

  users: [
    { id: 'u1', email: 'director@citi.ucc.edu.co', password: 'director2026', role: 'director', name: 'Dr. Carlos Méndez', meta: 'Director CITI · Sistemas y Civil' },
    { id: 'u2', email: 'coord.sistemas@citi.ucc.edu.co', password: 'coord2026', role: 'coordinador', name: 'Ing. Laura Vargas', meta: 'Coordinadora · Sistemas', area: 'sistemas' },
    { id: 'u3', email: 'coord.civil@citi.ucc.edu.co', password: 'coord2026', role: 'coordinador', name: 'Ing. Andrés Ríos', meta: 'Coordinador · Civil', area: 'civil' },
    { id: 'u4', email: 'docente@citi.ucc.edu.co', password: 'docente2026', role: 'docente', name: 'Mg. Patricia Gómez', meta: 'Docente asesora · Sistemas', area: 'sistemas' },
    { id: 'u5', email: 'docente.civil@citi.ucc.edu.co', password: 'docente2026', role: 'docente', name: 'Mg. Roberto Sánchez', meta: 'Docente asesor · Civil', area: 'civil' },
    { id: 'u6', email: 'consultor@citi.ucc.edu.co', password: 'estud2026', role: 'estudiante', studentType: 'consultor', name: 'Santiago Pérez', meta: 'Consultor recepción · 9° semestre' },
    { id: 'u7', email: 'tutor@citi.ucc.edu.co', password: 'estud2026', role: 'estudiante', studentType: 'tutor', name: 'María Fernanda López', meta: 'Tutora · 5° semestre · Sistemas', area: 'sistemas' },
    { id: 'u8', email: 'tutor.civil@citi.ucc.edu.co', password: 'estud2026', role: 'estudiante', studentType: 'tutor', name: 'Juan David Castro', meta: 'Tutor · 6° semestre · Civil', area: 'civil' },
    { id: 'u9', email: 'gerente@constructoratolima.com', password: 'cliente2026', role: 'cliente', name: 'Constructora del Tolima S.A.S.', meta: 'Construcción · Ibagué', empresaId: 'emp1' },
    { id: 'u10', email: 'admin@techpyme.com', password: 'cliente2026', role: 'cliente', name: 'TechPyME Soluciones', meta: 'Tecnología · Ibagué', empresaId: 'emp2' },
  ],

  permissions: {
    director: {
      can: [
        'Gestionar usuarios del consultorio',
        'Ver métricas globales y todos los casos',
        'Configurar semestre y líneas de acción',
        'Generar informes a directivas UCC',
        'Supervisar banco de empresas',
      ],
      cannot: [
        'Firmar informes como empresa',
        'Ejecutar tutorías en nombre de estudiantes',
      ],
    },
    coordinador: {
      can: [
        'Aprobar solicitudes de su área',
        'Asignar tutores y docentes',
        'Registrar visitas empresariales',
        'Supervisar estudiantes del área',
        'Enviar informe mensual al director',
      ],
      cannot: [
        'Gestionar usuarios del sistema',
        'Aprobar casos de otra área',
        'Configuración global del semestre',
      ],
    },
    docente: {
      can: [
        'Supervisar tutorías asignadas',
        'Revisar y aprobar informes de tutores',
        'Impartir talleres y seminarios',
        'Evaluar prácticas empresariales',
      ],
      cannot: [
        'Aprobar nuevas solicitudes de empresas',
        'Asignar casos sin coordinador',
        'Gestionar usuarios',
      ],
    },
    estudiante: {
      can: [
        'Recepción: registrar consultas y correspondencia (consultor)',
        'Recepción: bolsa de empleo y programa radial (consultor)',
        'Tutoría: ejecutar casos asignados (tutor)',
        'Tutoría: subir informes parciales mensuales (tutor)',
      ],
      cannot: [
        'Aprobar solicitudes o asignar casos',
        'Firmar informes finales',
        'Acceder a paneles de director o coordinador',
      ],
    },
    cliente: {
      can: [
        'Solicitar asesoría, capacitación o práctica',
        'Consultar estado de sus casos',
        'Firmar informes finales',
        'Ver historial de su empresa',
      ],
      cannot: [
        'Ver datos de otras empresas',
        'Asignar tutores o modificar informes',
        'Acceder a portales internos UCC',
      ],
    },
  },

  /** Casos de uso cubiertos por rol (referencia documento CITI) */
  casosUso: {
    cliente: ['CU-01 Solicitar asesoría', 'CU-02 Consultar casos', 'CU-03 Firmar informe'],
    estudiante_consultor: ['CU-04 Registro consultas', 'CU-05 Correspondencia', 'CU-06 Radial / empleo'],
    estudiante_tutor: ['CU-11 Ejecutar caso', 'CU-12 Informe parcial'],
    coordinador: ['CU-07 Aprobar solicitud', 'CU-08 Asignar equipo', 'CU-09 Visitas', 'CU-10 Informe área'],
    docente: ['CU-13 Revisar informe', 'CU-14 Talleres', 'CU-15 Prácticas'],
    director: ['CU-16 Usuarios', 'CU-17 Métricas', 'CU-18 Configuración', 'CU-19 Informe UCC'],
  },

  solicitudes: [
    { id: 'sol1', empresaId: 'emp1', empresa: 'Constructora del Tolima', area: 'civil', tipo: 'Asesoría', estado: 'en_proceso', tutor: 'Juan David Castro', docente: 'Mg. Roberto Sánchez', fecha: '2026-02-10' },
    { id: 'sol2', empresaId: 'emp2', empresa: 'TechPyME Soluciones', area: 'sistemas', tipo: 'Asesoría', estado: 'pendiente', tutor: null, docente: null, fecha: '2026-03-01' },
    { id: 'sol3', empresaId: 'emp1', empresa: 'Constructora del Tolima', area: 'sistemas', tipo: 'Taller', estado: 'completado', tutor: 'María Fernanda López', docente: 'Mg. Patricia Gómez', fecha: '2026-01-15' },
  ],

  consultas: [
    { id: 'c1', fecha: '2026-03-05', empresa: 'Cooperativa Agrícola', consulta: 'Necesitan página web', atendido: 'Santiago Pérez', area: 'sistemas' },
    { id: 'c2', fecha: '2026-03-06', empresa: 'Urbanizadora El Bosque', consulta: 'Revisión planos VIS', atendido: 'Santiago Pérez', area: 'civil' },
  ],
};

if (typeof module !== 'undefined') module.exports = CITI_DATA;
