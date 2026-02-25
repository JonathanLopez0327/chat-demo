# Catálogo de Incidentes – Fábrica de Huevos

## Objetivo
Este catálogo estandariza los incidentes que pueden surgir en una fábrica de huevos durante clasificación, empaque, almacenamiento y despacho, incluyendo incidentes de máquinas, proceso, calidad, inocuidad, seguridad y operación.

---

## Estructura sugerida del catálogo (para usar en sistema)

Cada incidente puede incluir:

- **Código**
- **Categoría**
- **Subcategoría**
- **Nombre del incidente**
- **Descripción**
- **Impacto**
- **Severidad** (Baja / Media / Alta / Crítica)
- **Acción inmediata sugerida**
- **Área responsable**

---

## Categorías del catálogo

- **MEC**: Maquinaria y equipos
- **PRO**: Proceso productivo
- **CAL**: Calidad e inocuidad
- **SEG**: Seguridad industrial y salud ocupacional
- **LOG**: Materiales, logística y almacenamiento
- **OPS**: Operación, personal y sistemas

---

# A. Incidentes de Maquinaria y Equipos (MEC)

## MEC-001 – Paro inesperado de clasificadora (grader)
- **Descripción:** La máquina clasificadora se detiene sin orden del operador.
- **Impacto:** Producción detenida.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Detener alimentación de producto, verificar alarma, escalar a mantenimiento.
- **Área responsable:** Mantenimiento / Producción

## MEC-002 – Atasco en banda transportadora
- **Descripción:** Huevos o bandejas se acumulan y bloquean el avance.
- **Impacto:** Roturas, retrasos y posible paro de línea.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Parar banda con procedimiento seguro y retirar atasco.
- **Área responsable:** Producción / Mantenimiento

## MEC-003 – Sensor de conteo/presencia con lectura errónea
- **Descripción:** El sensor no detecta correctamente huevos o registra conteos incorrectos.
- **Impacto:** Errores de empaque e inventario.
- **Severidad sugerida:** Media
- **Acción inmediata:** Limpiar sensor, revisar cableado y recalibrar.
- **Área responsable:** Mantenimiento / Producción

## MEC-004 – Calibración incorrecta de peso/tamaño
- **Descripción:** La clasificadora asigna mal la categoría del huevo.
- **Impacto:** Mezcla de calibres, reclamos comerciales.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Detener lote, recalibrar equipo y retener producto afectado.
- **Área responsable:** Mantenimiento / Calidad / Producción

## MEC-005 – Falla de motor / variador (VFD)
- **Descripción:** Motor no arranca, se apaga o presenta sobrecalentamiento.
- **Impacto:** Paro parcial o total de línea.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Aislar equipo y solicitar diagnóstico.
- **Área responsable:** Mantenimiento

## MEC-006 – Falla neumática (si aplica)
- **Descripción:** Actuadores/cilindros no responden por baja presión o fugas.
- **Impacto:** Rechazo incorrecto o movimientos incompletos.
- **Severidad sugerida:** Media
- **Acción inmediata:** Revisar presión, válvulas, mangueras y compresor.
- **Área responsable:** Mantenimiento

## MEC-007 – Falla en impresora de etiquetas/lote
- **Descripción:** La impresora no imprime, imprime ilegible o con información errónea.
- **Impacto:** Trazabilidad comprometida.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Detener etiquetado, corregir configuración/insumo y validar impresión.
- **Área responsable:** Producción / Calidad / Mantenimiento

## MEC-008 – Selladora de empaque defectuosa (si aplica)
- **Descripción:** Sellado incompleto, abierto o inconsistente.
- **Impacto:** Riesgo de contaminación y reclamos.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Ajustar parámetros y verificar lote procesado.
- **Área responsable:** Producción / Mantenimiento / Calidad

## MEC-009 – Lavadora de huevos fuera de servicio (si existe)
- **Descripción:** La máquina de lavado no opera correctamente o se detiene.
- **Impacto:** Afectación de higiene/calidad.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Detener proceso dependiente, evaluar producto afectado y escalar.
- **Área responsable:** Mantenimiento / Calidad / Producción

## MEC-010 – Falla en sistema de refrigeración / cámara
- **Descripción:** Temperatura fuera de rango en almacenamiento o producto terminado.
- **Impacto:** Calidad, inocuidad, vida útil.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Activar contingencia, mover producto a zona segura, registrar tiempo de exposición.
- **Área responsable:** Mantenimiento / Calidad / Almacén

## MEC-011 – Falla de energía eléctrica / microcortes
- **Descripción:** Interrupción o fluctuación eléctrica afecta operación y equipos.
- **Impacto:** Paros, pérdida de datos, daño de equipos.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Ejecutar protocolo de reinicio seguro y verificación de equipos.
- **Área responsable:** Mantenimiento / Producción / TI (si aplica)

## MEC-012 – PLC/HMI sin comunicación
- **Descripción:** El controlador o panel de operación pierde comunicación o no responde.
- **Impacto:** Imposibilidad de operar o monitorear línea.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Reinicio controlado y diagnóstico de comunicación.
- **Área responsable:** Mantenimiento / Automatización

---

# B. Incidentes del Proceso Productivo (PRO)

## PRO-001 – Alto porcentaje de huevos rotos en línea
- **Descripción:** Incremento de roturas por encima del límite aceptable.
- **Impacto:** Merma y pérdida de eficiencia.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Reducir velocidad, revisar puntos de impacto/transferencia.
- **Área responsable:** Producción / Mantenimiento / Calidad

## PRO-002 – Alto porcentaje de huevos sucios
- **Descripción:** Lote con suciedad visible por encima del estándar.
- **Impacto:** Reproceso, rechazo, baja calidad.
- **Severidad sugerida:** Media
- **Acción inmediata:** Segregar lote y notificar a calidad/origen.
- **Área responsable:** Calidad / Producción / Recepción

## PRO-003 – Mezcla de tamaños/categorías en un mismo empaque
- **Descripción:** Empaques contienen huevos de calibres diferentes.
- **Impacto:** Incumplimiento comercial, reclamos.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Retener lote, verificar calibración y clasificación.
- **Área responsable:** Producción / Calidad

## PRO-004 – Conteo incorrecto por empaque
- **Descripción:** Bandejas/cajas con menos o más unidades de las requeridas.
- **Impacto:** Diferencias de inventario y facturación.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Detener línea y validar sistema de conteo.
- **Área responsable:** Producción / Mantenimiento / Calidad

## PRO-005 – Error en lote / fecha de producción / vencimiento
- **Descripción:** Impresión o registro incorrecto de lote/fechas.
- **Impacto:** Trazabilidad y cumplimiento regulatorio.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Inmovilizar lote y corregir etiquetado/registro.
- **Área responsable:** Calidad / Producción

## PRO-006 – Producto mezclado entre lotes
- **Descripción:** Se mezclan huevos de lotes distintos sin control.
- **Impacto:** Pérdida de trazabilidad.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Detener, segregar e identificar producto involucrado.
- **Área responsable:** Producción / Calidad / Almacén

## PRO-007 – Retraso en arranque de turno
- **Descripción:** El inicio de línea ocurre después del horario planificado.
- **Impacto:** Afectación al plan de producción.
- **Severidad sugerida:** Media
- **Acción inmediata:** Registrar causa (personal, equipo, material, energía).
- **Área responsable:** Producción / Supervisión

## PRO-008 – Falta de material de empaque
- **Descripción:** No hay cartones, etiquetas, bandejas u otro insumo necesario.
- **Impacto:** Paro de línea.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Escalar a almacén/compras y activar contingencia.
- **Área responsable:** Almacén / Producción / Compras

## PRO-009 – Cambio de formato lento / setup prolongado
- **Descripción:** El cambio entre presentaciones tarda más de lo estándar.
- **Impacto:** Pérdida de disponibilidad y productividad.
- **Severidad sugerida:** Media
- **Acción inmediata:** Registrar tiempo/causa y comparar contra estándar.
- **Área responsable:** Producción / Supervisión / Mantenimiento

## PRO-010 – Acumulación de producto en buffer/mesa
- **Descripción:** Desbalance entre estaciones provoca acumulación.
- **Impacto:** Riesgo de rotura, desorden de flujo.
- **Severidad sugerida:** Media
- **Acción inmediata:** Balancear velocidades y revisar cuellos de botella.
- **Área responsable:** Producción / Mantenimiento

---

# C. Incidentes de Calidad e Inocuidad (CAL)

## CAL-001 – Huevo roto con derrame sobre producto sano
- **Descripción:** Contaminación cruzada por contacto con contenido de huevo roto.
- **Impacto:** Inocuidad y calidad del lote.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Retirar producto afectado, limpiar y sanitizar área.
- **Área responsable:** Calidad / Producción

## CAL-002 – Huevos fisurados no detectados
- **Descripción:** Huevos con grietas pasan a empaque final.
- **Impacto:** Reclamos y riesgo de contaminación.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Reforzar inspección y revisar sistema de detección.
- **Área responsable:** Calidad / Producción / Mantenimiento

## CAL-003 – Superficie de contacto sucia
- **Descripción:** Mesas, bandas, guías u otros puntos de contacto presentan suciedad/residuos.
- **Impacto:** Riesgo de contaminación.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Detener si aplica, limpiar y sanitizar según procedimiento.
- **Área responsable:** Calidad / Producción / Saneamiento

## CAL-004 – Limpieza/Sanitización no ejecutada o incompleta
- **Descripción:** No se ejecutó la limpieza programada o quedó incompleta.
- **Impacto:** Riesgo sanitario y no conformidad.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Bloquear arranque/liberación hasta completar y verificar.
- **Área responsable:** Calidad / Producción / Saneamiento

## CAL-005 – Temperatura fuera de especificación (almacenamiento)
- **Descripción:** Temperatura de almacenamiento fuera del rango definido.
- **Impacto:** Vida útil, calidad e inocuidad.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Evaluar tiempo de exposición, retener lote si aplica.
- **Área responsable:** Calidad / Almacén / Mantenimiento

## CAL-006 – Evidencia de plaga en proceso o almacén
- **Descripción:** Presencia de insectos, roedores o evidencia asociada.
- **Impacto:** Riesgo crítico de inocuidad.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Aislar área/producto y activar protocolo de control de plagas.
- **Área responsable:** Calidad / Saneamiento / Mantenimiento / Almacén

## CAL-007 – Material de empaque contaminado o dañado
- **Descripción:** Bandejas/cajas sucias, húmedas, deformadas o contaminadas.
- **Impacto:** Calidad y presentación del producto.
- **Severidad sugerida:** Media
- **Acción inmediata:** Bloquear lote de empaque y reemplazar material.
- **Área responsable:** Calidad / Almacén / Producción

## CAL-008 – Error de trazabilidad (registro incompleto)
- **Descripción:** Falta información de lote, turno, línea, operador o fecha.
- **Impacto:** Imposibilidad de rastreo.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Completar registro y evaluar alcance del producto afectado.
- **Área responsable:** Calidad / Producción / Supervisión

## CAL-009 – Desviación de BPM por manipulador
- **Descripción:** Incumplimiento de prácticas higiénicas (uniforme, lavado de manos, etc.).
- **Impacto:** Riesgo de contaminación y no conformidad.
- **Severidad sugerida:** Media
- **Acción inmediata:** Corregir en el momento y registrar.
- **Área responsable:** Calidad / Supervisión / Producción

## CAL-010 – Hallazgo de cuerpo extraño (no biológico)
- **Descripción:** Presencia de fragmentos de plástico, cartón, metal u otros.
- **Impacto:** Riesgo crítico para consumidor.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Detener línea, retener lote e investigar fuente.
- **Área responsable:** Calidad / Producción / Mantenimiento

---

# D. Incidentes de Seguridad Industrial y Salud Ocupacional (SEG)

## SEG-001 – Resbalón o caída en área de proceso
- **Descripción:** Caída por piso húmedo, derrame o señalización insuficiente.
- **Impacto:** Lesión al personal.
- **Severidad sugerida:** Media a Alta (según lesión)
- **Acción inmediata:** Atender colaborador, asegurar área, limpiar y señalizar.
- **Área responsable:** Seguridad / Producción / Saneamiento

## SEG-002 – Atrapamiento menor en banda/rodillo
- **Descripción:** Incidente o riesgo por manipulación cerca de partes móviles.
- **Impacto:** Seguridad del personal.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Activar paro de emergencia, evaluar lesión e investigar.
- **Área responsable:** Seguridad / Producción / Mantenimiento

## SEG-003 – Uso incorrecto o ausencia de EPP
- **Descripción:** Operador sin equipo de protección requerido.
- **Impacto:** Riesgo de accidente e inocuidad.
- **Severidad sugerida:** Media
- **Acción inmediata:** Corregir de inmediato y registrar incumplimiento.
- **Área responsable:** Seguridad / Supervisión / Producción

## SEG-004 – Activación de paro de emergencia
- **Descripción:** Se activa E-stop por condición insegura o incidente.
- **Impacto:** Paro de línea y posible riesgo de seguridad.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Verificar causa y liberar equipo bajo procedimiento.
- **Área responsable:** Producción / Seguridad / Mantenimiento

## SEG-005 – Riesgo eléctrico detectado
- **Descripción:** Cable expuesto, chispa, olor a quemado o tablero en mal estado.
- **Impacto:** Riesgo crítico para personas/equipos.
- **Severidad sugerida:** Crítica
- **Acción inmediata:** Aislar zona, no operar equipo y llamar técnico autorizado.
- **Área responsable:** Mantenimiento / Seguridad

## SEG-006 – Fuga de agua/aire/químico de limpieza
- **Descripción:** Derrame o fuga en equipos, líneas o área de proceso.
- **Impacto:** Seguridad, operación e inocuidad (según sustancia).
- **Severidad sugerida:** Media a Alta
- **Acción inmediata:** Contener, señalizar y limpiar según protocolo.
- **Área responsable:** Mantenimiento / Seguridad / Producción / Saneamiento

## SEG-007 – Incidente con montacargas/patín
- **Descripción:** Golpe a estantería, pallet, producto o infraestructura.
- **Impacto:** Riesgo de lesiones y daño material.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Asegurar área, evaluar daños y reportar.
- **Área responsable:** Almacén / Seguridad

---

# E. Incidentes de Materiales, Logística y Almacenamiento (LOG)

## LOG-001 – Recepción de huevos con daño excesivo
- **Descripción:** Lote recibido con alta rotura/fisura.
- **Impacto:** Merma y posible reclamo a proveedor/origen.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Separar lote, documentar evidencia y notificar.
- **Área responsable:** Recepción / Calidad / Almacén

## LOG-002 – Recepción sin documentación o datos incompletos
- **Descripción:** Falta guía, lote, origen, fecha u otros datos requeridos.
- **Impacto:** Trazabilidad comprometida.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Poner en cuarentena hasta validación documental.
- **Área responsable:** Recepción / Calidad / Almacén

## LOG-003 – Error de despacho (producto equivocado)
- **Descripción:** Se despacha presentación, calibre o lote incorrecto.
- **Impacto:** Devoluciones, reclamos y costos logísticos.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Bloquear salida si es posible y notificar a logística/comercial.
- **Área responsable:** Almacén / Despacho / Calidad

## LOG-004 – Daño de producto en almacenamiento
- **Descripción:** Roturas por mal apilado, mala manipulación o pallet defectuoso.
- **Impacto:** Merma.
- **Severidad sugerida:** Media
- **Acción inmediata:** Reacomodo seguro y segregación del producto dañado.
- **Área responsable:** Almacén

## LOG-005 – FIFO/FEFO no respetado
- **Descripción:** No se despacha según prioridad de fecha/lote.
- **Impacto:** Riesgo de vencimiento y pérdidas.
- **Severidad sugerida:** Alta
- **Acción inmediata:** Corregir picking y revisar control de inventario.
- **Área responsable:** Almacén / Despacho / Calidad

## LOG-006 – Falta de espacio en producto terminado
- **Descripción:** Saturación en almacén o cámara de producto terminado.
- **Impacto:** Retraso de producción y despacho.
- **Severidad sugerida:** Media
- **Acción inmediata:** Coordinar despacho/redistribución y priorizar salidas.
- **Área responsable:** Almacén / Producción / Logística

---

# F. Incidentes de Operación, Personal y Sistemas (OPS)

## OPS-001 – Ausencia de operador clave en estación crítica
- **Descripción:** No hay personal disponible para una estación esencial.
- **Impacto:** Reducción de capacidad o paro.
- **Severidad sugerida:** Media
- **Acción inmediata:** Reasignar personal y escalar a supervisión.
- **Área responsable:** Producción / Supervisión / RRHH (si aplica)

## OPS-002 – Error de captura en registro hora por hora
- **Descripción:** Cantidades, tiempos, lotes o causas mal registradas.
- **Impacto:** Datos inexactos para análisis y trazabilidad.
- **Severidad sugerida:** Media
- **Acción inmediata:** Corregir registro con validación de supervisor.
- **Área responsable:** Producción / Supervisión / Calidad

## OPS-003 – Usuario no puede registrar incidente en sistema/PWA
- **Descripción:** Falla de acceso, permisos, red o aplicación.
- **Impacto:** Pérdida de trazabilidad en tiempo real.
- **Severidad sugerida:** Media
- **Acción inmediata:** Registrar manualmente de forma temporal y escalar a soporte.
- **Área responsable:** TI / Producción / Supervisión

## OPS-004 – Caída de red/WiFi en planta
- **Descripción:** Dispositivos no sincronizan información con el sistema.
- **Impacto:** Afectación de operación digital y registros.
- **Severidad sugerida:** Media
- **Acción inmediata:** Activar contingencia offline/manual y notificar TI.
- **Área responsable:** TI / Producción

## OPS-005 – Procedimiento no seguido / desviación operativa
- **Descripción:** Se ejecuta una actividad fuera del SOP/estándar.
- **Impacto:** Calidad, seguridad y eficiencia.
- **Severidad sugerida:** Media a Alta (según impacto)
- **Acción inmediata:** Corregir, registrar y evaluar necesidad de capacitación.
- **Área responsable:** Producción / Calidad / Supervisión

---

# Catálogo de causas raíz comunes (opcional)

## Causas técnicas
- Descalibración
- Falta de mantenimiento preventivo
- Pieza desgastada
- Sensor sucio/dañado
- Falla eléctrica
- Falla neumática
- Configuración incorrecta
- Falla de PLC/HMI/software industrial

## Causas operativas
- Error de operador
- Falta de capacitación
- No seguimiento de SOP
- Fatiga / distracción
- Arranque apresurado
- Ajuste manual incorrecto
- Falta de supervisión

## Causas de materiales
- Insumo defectuoso
- Material de empaque fuera de especificación
- Falta de insumos
- Recepción deficiente
- Mal almacenamiento

## Causas de entorno / gestión
- Falta de energía
- Fallo de red/WiFi
- Temperatura ambiente fuera de control
- Falta de personal
- Planificación deficiente
- Limpieza insuficiente

---

# Campos recomendados para registrar cada incidente en tu sistema (PWA/MES)

- `incident_code`
- `incident_name`
- `category` (MEC, PRO, CAL, SEG, LOG, OPS)
- `sub_category`
- `severity` (LOW, MEDIUM, HIGH, CRITICAL)
- `date_time_reported`
- `reported_by`
- `plant`
- `line`
- `work_cell`
- `machine` (opcional)
- `production_order` (recomendado)
- `lot_number` (si aplica)
- `shift`
- `description`
- `immediate_action`
- `status` (OPEN, IN_PROGRESS, CONTAINED, CLOSED)
- `root_cause` (opcional al cierre)
- `corrective_action` (opcional al cierre)
- `preventive_action` (opcional al cierre)
- `attachments` (fotos/evidencias)
- `closed_by`
- `closed_at`

---

# Recomendación práctica para tu demo/MVP

Para comenzar, puedes implementar primero estas **10 incidencias prioritarias** (más comunes y útiles):

1. `MEC-002` Atasco en banda transportadora  
2. `MEC-004` Calibración incorrecta de peso/tamaño  
3. `MEC-010` Falla en refrigeración/cámara  
4. `PRO-001` Alto porcentaje de huevos rotos  
5. `PRO-005` Error en lote/fecha  
6. `CAL-001` Huevo roto con derrame sobre producto sano  
7. `CAL-003` Superficie de contacto sucia  
8. `CAL-010` Hallazgo de cuerpo extraño  
9. `SEG-001` Resbalón/caída  
10. `OPS-002` Error de captura en registro hora por hora

---