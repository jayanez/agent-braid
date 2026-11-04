<!-- Provenance: verbatim copy of the UX audit of 2026-11-04 (Spanish; the repository's public documentation is English,
this file is retained as source evidence, summarized in ../README.md and ../skill-lens-findings.md). Line references were
valid for develop at e8060ac5 and may have moved. Synthetic fixture only; no owner data. Not an approval. -->

# Auditoria UX del visor de actividad "Loom" (SPEC-061 VIS.1a)

Rama `develop` @ e8060ac5. Solo lectura: no se toco el repo. Instancia propia en `127.0.0.1:8791` con un replay sintetico
(`fixture/rich.jsonl`, 34 eventos, 9 carriles; generador `fixture/gen.py`; valida con `agent-braid view validate`).
El visor del propietario (`:8765`) no se uso: su codigo de apertura es de un solo uso.
Capturas en `screenshots/`. Rutas de codigo relativas a `integrations/agent-braid-view/web/` salvo que se indique.

**Como se establecio cada hallazgo**: [M] medido en el navegador, [C] leido en codigo, [I] inferido de capturas.
**Lentes aplicadas**: ui-ux-review (conductor; app pequena, <15 ficheros UI, asi que sin subagentes: a11y, ux, system, measure, aesthetic aplicados en una sola pasada),
dataviz (codificacion, leyenda, color, diseno de la linea de tiempo 2D) y Context7 para Three.js r186. Las listas de web-design-guidelines,
design:accessibility-review, emil-design-eng y apple-design se aplicaron de memoria como checklists (no se cargaron como Skills por separado);
la revision de movimiento es por codigo, no por captura de video. **No se probo con un lector de pantalla real ni con datos reales del propietario.**

## 1. Resumen ejecutivo

El visor es fiel al contrato (todo elemento = un evento, nada afirma garantias) pero esta disenado desde el modelo, no desde la pregunta del usuario.
El usuario pregunta "que agente hizo que, cuando, cuanto tardo y donde choco". La pagina responde "que clases de compatibilidad tiene cada par".
Causas raiz, en orden de impacto:

1. **El eje X no es tiempo legible.** El modelo comprime todo hueco >5 s a 0,5 s (`agent_braid/view_model.py:118-146`), el 3D reescala todo a 24 unidades
   (`braid-scene.js:36,130`) y la web **nunca muestra** `axis.compressions` (grep: cero usos). 10 s y 500 ms se ven igual. No hay duracion en ningun sitio. [M][C]
2. **La camara y la escena son ilegibles al abrir.** Los anillos de puerta/concesion tienen radio del tamano de toda la escena y dominan el encuadre; las etiquetas
   (sprites con `depthTest:false`) se solapan en el cluster de eventos. Zoom y orbita no tienen limites ni inercia ni teclado. [M] (`01`, `03`, `05`)
3. **Informacion clave ausente**: agente activo ahora, estado (corriendo/esperando/terminado), duracion por agente, conflicto en lenguaje humano. Los datos existen
   en parte (`strand.update.state/toolName`, apertura/cierre con `relMs`, `parentStrandId`) pero la UI no los usa. [C]
4. **Jerarquia de pagina equivocada**: 4200 px de alto, aviso legal largo arriba, evidencia en columna no fija que se pierde al seleccionar en el 3D, leyenda
   solo en texto (sin muestras de color/forma), 34/34 eventos marcados "unverified" (la alerta pierde senal). [M]
5. **Accesibilidad de teclado/lector**: canvas no enfocable, sin teclas, la rueda sobre el canvas atrapa el scroll de pagina. [M]

Recomendacion: (a) arreglar camara/labels/leyenda del 3D como parche rapido (Fase 1), (b) anadir una **vista 2D de lineas de tiempo en SVG** como vista
por defecto (Fase 2), con estado y filtros compartidos, y (c) dejar el 3D como vista secundaria "espacial". La 2D es posible sin tocar dependencias ni CSP (seccion 6).
Esto **contradice la decision de ADR 0033** ("SVG 2D... no como superficie primaria que el propietario eligio"): necesita decision explicita del propietario.

## 2. Hallazgos

### P0 (bloquean entender o usar la vista)

**P0-1. No se puede leer el tiempo ni la duracion.** [M][C]
- Evidencia: `view_model.py:118-146` comprime huecos; `loom.js` no referencia `axis`; el `timeText` solo muestra `relMs` crudo (`loom.js:160-163`: "114000 ms").
  En `04-scene-orbit.png` los eventos de 100 s a 115 s (analisis, ondas) quedan apilados en ~1 unidad mientras los primeros 95 s ocupan media escena.
- Impacto: no responde "cuanto tardo". Un hueco de 6 minutos es invisible. Riesgo de lectura erronea (parece simultaneo).
- Arreglo: eje proporcional por defecto con ruptura de eje visible y etiquetada ("−6 min 20 s", usando `axis.compressions`); formateo `m:ss`; duracion por carril = cierre−apertura; para carriles abiertos, duracion hasta "ahora" (ver brechas de datos).

**P0-2. Encuadre inicial y objetos dominantes rompen la escena.** [M][C]
- Evidencia: `01-desktop-light-initial.png`: el hexagono rojo (gate `hazards-found`) y los anillos azul/gris ocupan >60 % del canvas y se cortan por el borde; los carriles reales
  quedan en una franja minima. Codigo: radio del anillo = `max(1.25, spanZ/2+1.0)` (`braid-scene.js:476`), `fit()` encuadra *todo* incluido eso (695-719).
  Los anillos son un plano perpendicular al tiempo, por lo que desde la vista inicial parecen "paredes".
- Impacto: la primera impresion es caos; el usuario no encuentra los agentes.
- Arreglo: encuadrar solo carriles+eventos (Box3 de grupo "agentes"), representar puertas/concesiones como marcadores en un carril superior ("Gobierno") en vez de anillos gigantes; ver seccion 4.

**P0-3. Etiquetas ilegibles y solapadas.** [M][C]
- Evidencia: `05-scene-zoom.png` ("Edit README", "Edit ROADMAP", "class 0", "wave 0 started" superpuestas); sprites con `depthTest:false`, tamano en unidades de mundo (`braid-scene.js:536-572, 205-211`), cap 400 sin colision.
  Al alejar el texto es microscopico (`04`), al acercar es enorme (`05`).
- Arreglo: etiquetas HTML (CSS2DRenderer) con tamano fijo en px y anti-colision; etiqueta de carril anclada al borde izquierdo siempre visible; resto solo en hover/seleccion.

**P0-4. Sin respuesta a "que agente esta activo / que paso / que choco".** [C]
- Evidencia: `strand.update` (`state: running|waiting|idle`, `toolName`) solo aparece como una bolita gris (`drawBead`, `braid-scene.js:496-507`); un carril sin cierre se dibuja hasta
  `TIME_LENGTH` (`braid-scene.js:234`), asi que *en curso* es indistinguible de *duro todo el rato*; el conflicto es un nudo toroidal de 0,2 u. con etiqueta "class 0" (jerga).
- Arreglo: estado por carril (chip + cursor "ahora"), conflicto con texto "Edit ROADMAP y Second ROADMAP edit tocan ROADMAP.md" (usa `sharedResources`, `reasons`).

### P1

**P1-1. Camara: sin inercia, sin limites, sin teclado, rueda secuestra el scroll.** [M][C]
- `new OrbitControls(camera, canvas)` solo con `screenSpacePanning=true` (`braid-scene.js:615-616`): sin `enableDamping`, `minDistance/maxDistance`, `maxPolarAngle`, `zoomToCursor`, `listenToKeyEvents`, `touches`. Medido: rueda sobre el canvas -> `scrollY` 165→165 (pagina atrapada); `touch-action:none` (`style.css`) atrapa tambien el scroll tactil en movil.
- Un clic en "Reset view" es el unico apoyo; sin ayuda de controles; `userMoved` desactiva el re-encuadre en resize (movil: escena recortada, `09-light-mobile-scene.png`).
- Arreglo: ver tabla de seccion 4.

**P1-2. Leyenda solo en texto, sin muestras.** [C] `loom.js:62-76` y `renderLegend` (224-235): 13 parrafos largos, "Grey shapes", "Amber wire octahedron"; cero swatches. El color por host (`HOST_COLORS`, `braid-scene.js:69`: azul/naranja/verde) no figura en ninguna leyenda con color, y "Replay file / Hook and telemetry ingest" es jerga de implementacion.
- Arreglo: leyenda compacta con iconos SVG identicos a los de la escena; filtro de leyenda clicable; el texto largo a un panel "Ayuda".

**P1-3. Detalle (evidencia) no esta junto a la seleccion.** [M] `aside` `position:static`, pagina de 4200 px; el estado de hover se pinta debajo del canvas (`#scene-hover`, `index.html:42`), no junto al cursor. Seleccionar en 3D no desplaza ni resalta el panel; hay que hacer scroll.
- Arreglo: panel de detalle sticky (o bottom sheet en movil), tooltip junto al cursor, "Esc" deselecciona.

**P1-4. Etiquetado de carriles ambiguo con subagentes del mismo tipo.** [C] `view_hooks.py:196-198`: etiqueta = `agent_type` (p. ej. "track-runner"); dos subagentes iguales -> dos carriles con el mismo nombre. El orden de carriles se hace por parejas de cruces (`view_model.py:71`) y pierde la jerarquia padre/hijo aunque `parentStrandId` existe.
- Arreglo: etiqueta "track-runner #2" calculada en la UI (ordinal por tipo y tiempo de apertura; sin nuevo dato), carriles agrupados bajo su padre.

**P1-5. Alerta "unverified" sin senal.** [M] 34/34 elementos con borde ambar discontinuo y octaedro ambar en 3D (`02-desktop-light-full.png`); en replay y hooks *todo* es unverified, asi que la marca no discrimina.
- Arreglo: marca de verificacion a nivel de fuente ("Fuente: hooks, no verificada" una vez, en la barra de filtros) y marca por evento solo para la excepcion (verificado o derivado). Mantener REQ-010 (marker distinto en crossing y gate): usar un icono pequeno, no octaedro 3D.

**P1-6. Tabla de 8 columnas desborda (1266 px en 916) y 34 tab stops de fila.** [M] `table-wrap` scroll horizontal; sin ordenar, sin busqueda; subject de eventos "strand state" es un id opaco. Movil `08-dark-mobile.png`.
- Arreglo: columnas por defecto Hora, Agente, Evento, Estado, Duracion; resto en detalle; tarjetas en movil; navegacion con flechas (roving tabindex) en vez de un boton por fila.

**P1-7. Directo (live): no hay "ahora".** [C] `scale = TIME_LENGTH/rawMax` (`braid-scene.js:129-131`) reescala la escena en cada evento; el modelo no expone reloj del servidor. El usuario no ve que algo sigue corriendo ni cuanto lleva.

### P2

- **P2-1. Reproduccion no reproduce tiempo.** Avanza 1 evento cada 700 ms (`loom.js:79`) aunque la linea de tiempo sea real; la nota lo admite ("does not replay real timing"). Ofrecer modo "tiempo real x N" ademas de "por eventos".
- **P2-2. Aviso no-claim ocupa el primer pliegue** (`index.html:20-21`) con tres chips tecnicos (`executionAuthorization: false`). Mantenerlo (gobernanza) pero como franja de una linea + "Acerca de".
- **P2-3. Pulsado permanente** (`braid-scene.js:656-669`) hace rAF continuo mientras haya material pulsante visible; respeta `prefers-reduced-motion` (bien) pero cuesta bateria. Pulsar solo en seleccion/hover.
- **P2-4. Tema oscuro correcto pero etiquetas del canvas se reconstruyen** con `rebuild()` al cambiar tema (`:838`), perdiendo camara si `fitted` ya es true no, pero si genera parpadeo. Bajo impacto.
- **P2-5. `title=` en 97 nodos** como unico soporte de significado (tooltips inexistentes en tactil). Mover a leyenda/ayuda visibles.
- **P2-6. Densidad de movimientos:** sin transiciones al seleccionar (la caja de seleccion aparece de golpe), sin easing en "Reset view" (salto). Animar 200-300 ms `easeOutCubic` la camara hacia el objetivo; respetar reduced motion.

### P3
- Fuente del sistema, sin jerarquia tipografica (todo 13,6-16 px); contraste de `--muted` correcto (#5a5a55 sobre blanco ≈ 6,9:1; no es problema).
- `h2` "Braid scene (3D)": "braid" es jerga interna; renombrar "Mapa espacial 3D".
- Textos de interfaz en ingles; el propietario trabaja en espanol. Preguntar si se internacionaliza.

### Lo que esta bien (conservar)
Todo elemento ligado a un evento; tabla como alternativa textual; aviso de no-garantia; ocultar fuente != ausente; focus visible 3 px; `prefers-reduced-motion` y `forced-colors` contemplados; botones >=36 px; sin horizontal scroll de pagina en 390 px; CSP estricta; cap de objetos.

## 3. Lo que el 3D hace y por que confunde (modelo mental)
Eje X tiempo, Z un carril por strand, Y casi nada. Los cruces son geometria en el plano; las clases son poligonos de 3+n lados con el mismo color; puertas/concesiones, anillos perpendiculares. Es un vocabulario de ~13 formas que el usuario debe memorizar (`loom.js:62-76`) y solo una (conflicto) responde a una pregunta de usuario. El tercer eje (Y) no codifica nada: el 3D no anade informacion que una 2D no tenga, solo cuesta camara y oclusion. Mantenerlo como vista espacial secundaria es razonable; no deberia ser la vista de decision.

## 4. Recomendaciones para el 3D (mapeadas a Three.js r186)
Capacidades confirmadas con Context7 (r186) y en el fichero vendorizado: `OrbitControls` tiene `enableDamping/dampingFactor`, `minDistance/maxDistance`, `maxPolarAngle`, `zoomToCursor` (:306), `listenToKeyEvents` (:585), `keyPanSpeed`, `saveState/reset`, `cursorStyle`, `touches`. `MapControls` no esta vendorizado (anadirlo requiere manifest); no hace falta.

| Necesidad | API Three.js | Nota |
|---|---|---|
| Inercia y limites | `controls.enableDamping=true; dampingFactor=0.08; minDistance/maxDistance` derivados del `Box3`; `maxPolarAngle=Math.PI*0.49` | con damping hay que llamar `controls.update()` en el bucle (cuidado con el modelo rAF-bajo-demanda: pedir frames mientras `controls` se mueve) |
| Zoom al cursor, pan natural | `zoomToCursor=true`, `screenSpacePanning=true`, `mouseButtons={LEFT:ROTATE,MIDDLE:DOLLY,RIGHT:PAN}`, `touches={ONE:ROTATE,TWO:DOLLY_PAN}` | |
| No atrapar scroll de pagina | `controls.enableZoom` solo con Ctrl/Cmd+rueda o tras foco/clic; `touch-action:pan-y` en movil con modo "bloquear escena" | sobreescribir con `wheel` listener `passive:false` y `preventDefault` condicional |
| Teclado | `listenToKeyEvents(canvas)` + `canvas.tabIndex=0`, `role="application"` o mejor `role="group"` con `aria-describedby` a la ayuda; F = encuadrar, Esc = quitar seleccion | |
| Auto-encuadre | `new THREE.Box3().setFromObject(grupoAgentes)`; `getBoundingSphere`; distancia = `radio / sin(fov/2)` (o ajustar por aspect); animar `camera.position` y `controls.target` con tween 250 ms (easeOutCubic), respetando reduced-motion | sustituye `fit()` de 120 iteraciones (`braid-scene.js:695-719`); excluir anillos/slabs (usar `Layers`: capa 1 = encuadrables) |
| Vistas guiadas | presets Lateral (mirando -Z, tiempo horizontal = casi 2D), Cenital, Isometrica; botones | la lateral es lo que el usuario espera |
| Etiquetas legibles | `CSS2DRenderer` (`three/addons/renderers/CSS2DRenderer.js`, **nuevo fichero vendorizado**: manifest+hash, `BUNDLE_FILES`, import map -> cambia el hash CSP; ADR 0033 amendment) o, sin tocar vendor, **overlay HTML propio** posicionado con `vector.project(camera)` | el overlay propio evita ampliar el limite de vendor; coste: unos 40 lineas |
| Seleccion/hover | `Raycaster` ya existe (`:775-786`); anadir `raycaster.layers`, hit-target invisible mas grueso por carril (cilindro radio 0,25, `visible=false` no funciona: usar `material.visible=false` pero raycastable via `Mesh` con `colorWrite=false`) | tooltip HTML junto al cursor; `Esc` limpia |
| Lineas visibles a cualquier zoom | `Line2/LineMaterial` (fat lines, nuevos addons) o mantener `TubeGeometry` con radio en funcion de distancia | opcional |
| Rendimiento | `InstancedMesh` para balizas/cuentas/conos (hoy un `Mesh` por elemento, tope 12000 objetos); `renderer.setAnimationLoop` solo mientras haya inercia/pulso | |
| Resize | `ResizeObserver` ya esta; re-encuadrar tambien tras interaccion si el usuario pulsa "Encuadrar" | quitar la dependencia de `userMoved` |

Cambios de contenido del 3D: carriles agrupados por padre, gobernanza (concesiones/puertas) como marcadores en un carril superior, conflicto con icono grande rojo + texto, "ahora" como plano translucido, etiquetas de duracion al final del carril.

## 5. Propuesta de nueva vista 2D (lineas de tiempo, SVG)
Wireframes: `wireframes/01-layout-desktop.txt`, `02-timeline-2d.txt`, `03-3d-overlay.txt`, `04-timeline-2d.svg`.

**Modelo de pantalla.** Barra superior con resumen en una linea (duracion, n.º agentes, n.º conflictos, n.º huecos), selector de vista (2D | 3D), filtros y fuentes; vista principal; panel de detalle sticky; control de reproduccion; pestanas (Tabla, Resumen, Leyenda, Ayuda).

**Estado compartido (una sola fuente de verdad)** — hoy ya existe parcialmente en `loom.js` `state`; se amplia a:
`{ model, cursorMs, playing, speedMode, selectedSeq, hoveredSeq, hiddenSources, filters:{agent,status,onlyProblems,kind}, viewport:{t0,t1}, view:'2d'|'3d' }` + `derived` (`strands[]` con `{id,label,ordinal,parent,host,role,openMs,closeMs|null,state,durationMs,outcome,tools[],gaps[]}`; `conflicts[]` con los dos strands, recursos, razones). Las vistas son funciones puras `render(state, derived)`; el 3D recibe `visibleSeqs` como ahora. Una funcion `deriveStrands(model)` es el unico codigo nuevo de logica y se testea en Python-JS paridad con `view_model` (o se mueve al servidor, ver brechas).

**Codificacion (dataviz).**
- Eje X = tiempo proporcional (m:ss). Rupturas de eje explicitas con etiqueta de tiempo omitido (`axis.compressions`). Ticks "bonitos" (5/10/30 s, 1/5 min).
- Un carril por strand; hijos indentados bajo el padre (`parentStrandId`); etiqueta fija a la izquierda con ordinal.
- Barra = [apertura, cierre]; relleno solido = terminado, rayado = en curso (extremo derecho "▶ ahora"), punteado = cierre no observado/hueco; resultado (`outcome`) como icono al final (✓ ok, ✕ error, ? unknown, ⊘ cancelled).
- Color = host (3 tonos categoricos, orden fijo, validar con `validate_palette.js` en claro y oscuro) y **nunca** estado/riesgo; estado y conflicto = forma + texto + color rojo/ambar solo en iconos (los colores de estado son reservados; no usar para series). Etiquetas de texto en tinta, no en color de serie.
- Marcas finas dentro de la barra para `strand.update` (herramienta, `waiting` en hachurado) para ver "que hace ahora".
- Cruces: linea vertical entre dos carriles en el instante del evento con icono: ✕ conflicto (+ texto en tooltip con recursos compartidos), ⇄ independiente candidato, → ordenado, ? desconocido; mismas reglas REQ-010 (solo independiente = "swap"; nunca se pinta un desconocido como limpio).
- Gobernanza (ondas planificadas/ejecutadas, concesiones, puertas): carril superior fijo "Gobierno"; ondas planificadas = franjas translucidas "plan asesor, no medicion"; puertas/concesiones = iconos con etiqueta del estado.
- Peligros = triangulo sobre el carril del strand (relleno si observado; contorno discontinuo si "no observado", como hoy).
- Huecos de observacion = trazo gris discontinuo en el carril con icono ▯ y razon al hover.
- Hover = tooltip (agente, estado, inicio–fin, duracion, n.º herramientas); clic = detalle; teclas flechas navegan eventos; `aria-label` por barra (patron `role="listbox"` o tabla sincronizada).
- Leyenda: una linea con muestras reales (SVG identico), clicable para filtrar.
- Tabla y 2D comparten filas: la tabla es la alternativa textual (WCAG) y se sincroniza con el cursor.

**Interaccion.** Zoom en X con rueda+Ctrl/pellizco, pan arrastrando, doble clic = encuadrar, brush en la regla, cursor vertical de reproduccion; modo "en vivo" que sigue "ahora" con boton "Volver a ahora" si el usuario se desplaza.

**Rendimiento.** SVG hasta ~300 carriles x 2000 elementos; sobre eso, virtualizar por viewport o pasar a Canvas 2D. Agrupar updates con rAF.

**Restricciones que cumple.** Sin dependencias: SVG creado con `createElementNS` y atributos de presentacion; CSP `style-src 'self'` bloquea el atributo `style=` pero permite CSSOM (`el.style.x=`), clases CSS y atributos SVG (`fill`, `x`, `width`, `transform`); Trusted Types no afecta a `createElementNS`/`textContent`; todo texto como nodo de texto. Nuevo fichero `timeline.js` (y a lo sumo `timeline.css` o ampliar `style.css`) -> anadir a `BUNDLE_FILES` (`view_cli.py:51`) y a los tests de bundle. Sin cambio de import map si se carga con `import()` dinamico como `braid-scene.js`.

## 6. Brechas de datos / contrato
| Necesidad de la UI | Estado en `loom/v0.1` | Propuesta |
|---|---|---|
| Duracion de un agente | derivable: `strand.open`/`strand.close` con `relMs` (kept por el contrato de privacidad: "Sub-day relative time") | derivar en cliente o `model.lanes[].openMs/closeMs/durationMs`. No viola privacidad (no es efecto/coste) |
| "Ahora" / agente en curso | `axis.maxMs` = ultimo evento, no reloj del servidor | anadir `axis.nowMs` (reloj monotonic del servidor) al snapshot; sin cambio de esquema de evento |
| Estado actual de un agente | `strand.update.state` (running/waiting/idle) y `toolName` | solo UI; ojo: hooks solo emiten `PostToolUse`, asi que "running" se infiere por ultima actividad (umbral) — etiquetar "inferido" |
| Duracion de herramienta | no (el hook `PostToolUse` no esta en la allowlist con duracion; `tool_use_id` se descarta) | pedir al propietario si se permite campo de duracion (no contenido). Sin eso, solo marcas puntuales |
| Resultado del agente | hooks cierran siempre `outcome:"unknown"` (`view_hooks.py:23,209`) | mostrar "?" honesto; no inventar exito |
| Conflicto en tiempo de ejecucion | solo `crossing.classified: conflicting` (analisis previo, **prediccion**), no hay evento de colision real (merge conflict, rechazo de escritura, ownership) | decidir si VIS.1b anade `conflict.observed` desde `ownership-receipt`; hasta entonces rotular "conflicto detectado por analisis", no "ocurrio" |
| Espera/cola entre agentes | no hay evento "esperando por X" (solo `state: waiting` sin referencia) | opcional: `waitingOn` (id de strand) — identificadores salados, ya permitido |
| Etiquetas distintas por agente | `label`=`agent_type` | ordinal en cliente; sin nuevo dato |
| Esfuerzo (tokens/coste) por agente | existe `effort.sample`, **no se dibuja** y es efimero (REQ-007) | en la vista 2D, columna opcional en memoria, etiquetada `host-estimate`, nunca exportada por defecto |
| Texto de prompt/objetivo del agente | **prohibido** (no se retiene contenido de mensajes/prompt) | no proponer; usar `agent_type` + ordinal |
| Rutas/archivos | solo `evidenceRef` relativo y `sharedResources` (ids de recurso del analisis) | mostrar tal cual; nunca rutas absolutas (la pagina usa `root N`) |
| Marca de tiempo absoluta | prohibida | usar tiempo relativo "hace X" solo desde reloj del visor |

Privacidad: la vista 2D no necesita ningun campo que viole `ui-security-privacy.md`; las ampliaciones sugeridas (`nowMs`, `waitingOn`, duracion de herramienta) deben pasar por el mismo allowlist y por decision del propietario.

## 7. Restricciones que el rediseno debe respetar
- Servidor stdlib (`view_serve.py`), solo loopback, sin red saliente, sin dependencias nuevas (ADR 0032).
- Ficheros web: solo los de `BUNDLE_FILES` (`view_cli.py:51`) mas `vendor/` por manifest con sha256 (ADR 0033; propietario 2026-11-02: "solo lo del manifest"). Anadir `CSS2DRenderer`/`Line2`/`MapControls` = nuevo vendor -> recibo, manifest, hash, posible enmienda de ADR; preferir overlay HTML propio.
- CSP: `default-src 'self'; script-src 'self' 'sha256-<importmap>'; style-src 'self'; require-trusted-types-for 'script'` (`view_serve.py:353-366`): sin `style=` en HTML ni `<style>` inline, sin `innerHTML`; un segundo import map esta prohibido.
- Todo valor de evento como nodo de texto; sin `eval`/`Function`/URL remota (`tests/test_view_web_bundle.py`).
- Sin afirmar garantia, orden de seguridad ni speedup; `executionAuthorization:false` visible; clases = etiquetas categoricas, no ordenadas (REQ-010); desconocido/no observado nunca se pinta como limpio (REQ-003); color nunca unico portador de significado.
- Esfuerzo efimero y solo en memoria; exportes minimos; sin marcas de tiempo absolutas ni rutas absolutas.
- Tabla = alternativa textual completa; sin WebGL la pagina sigue util.
- El panel debe funcionar si lo ve un agente en un navegador integrado (el texto de la pagina entra en su contexto; evitar datos sensibles).

## 8. Plan por fases con criterios de aceptacion
**Fase 0 — Decisiones (0,5 d).** Propietario: 2D por defecto (enmienda de ADR 0033), idioma, hueco de conflicto en ejecucion, `nowMs`.
**Fase 1 — Parche rapido 3D + pagina (2-3 d).** Camara (damping, limites, zoomToCursor, teclado, scroll no atrapado, vistas lateral/cenital, encuadre solo agentes, animacion), etiquetas HTML sin colision, leyenda con muestras, panel de detalle sticky y tooltip, ayuda `?`, "Encuadrar", re-encuadre en resize.
 Aceptacion: al abrir el fixture `rich.jsonl` los 9 carriles caben y se leen sin tocar nada a 1440x900 y 390x844; ninguna etiqueta de carril se solapa; rueda sobre la pagina desplaza la pagina salvo Ctrl+rueda; Tab llega al canvas y F/flechas funcionan; "Encuadrar" restituye la vista en <400 ms; `tests/test_view_web_*` verdes.
**Fase 2 — Modelo derivado + vista 2D (4-6 d).** `deriveStrands`, `timeline.js`, estado compartido, ruptura de eje, duracion y estado por carril, cruces/conflictos con texto, filtros/fuentes compartidos, panel y tabla sincronizados, reproduccion por eventos y en tiempo.
 Aceptacion: con `rich.jsonl`, cada barra muestra inicio-fin-duracion exactos (verificados contra `relMs`); el hueco de 10 s aparece como ruptura etiquetada; el conflicto ROADMAP se localiza en <5 s (prueba con 3 usuarios o revision del propietario); misma seleccion en 2D/3D/tabla; modo oscuro y 390 px sin scroll horizontal; axe/a11y sin errores criticos; foco por teclado a cada barra; no hay `style=` ni violaciones CSP en consola.
**Fase 3 — Datos en vivo (1-2 d, requiere decision).** `axis.nowMs`, estado "en curso", seguimiento "ahora", `waitingOn`/`conflict.observed` si se aprueban.
 Aceptacion: un agente abierto crece en tiempo real; al cerrarse se fija; "en curso" vs "terminado" distinguibles en blanco y negro.
**Fase 4 — Pulido (2 d).** Tabla compacta/tarjetas movil, micro-animaciones (200-300 ms, reduced-motion), reduccion del chip unverified, i18n, rendimiento (InstancedMesh, pulso solo bajo demanda), pruebas de regresion visual con capturas.
 Aceptacion: Lighthouse a11y >=95 en ambos temas; 60 fps con 2000 elementos en el 3D; revision con lector de pantalla real (VoiceOver) del flujo "seleccionar conflicto".

## 9. Preguntas abiertas para el propietario
1. ¿La vista 2D de lineas de tiempo pasa a ser la **vista por defecto** (enmienda de ADR 0033, que decia que el 3D era la superficie primaria elegida)?
2. ¿Que significa "conflicto" para ti: la prediccion del analisis (`conflicting`), o una colision real durante la ejecucion? Hoy solo existe la primera.
3. ¿Aprobamos `axis.nowMs` y un campo de espera `waitingOn` y, si el hook lo ofrece, duracion de herramienta (sin contenido)?
4. ¿Idioma de la interfaz: espanol, ingles o ambos?
5. ¿Puedes compartir una captura/descripcion de lo que ves en `:8765` (solo hooks vs. hooks + analisis)? No pude abrir tu sesion.
6. ¿Aceptas ampliar el vendor (CSS2DRenderer/Line2) o preferimos solo overlays propios?
7. ¿Quieres que los textos largos de gobernanza se mantengan siempre visibles o moverlos a "Acerca de"?

## 10. Archivos
- Capturas: `screenshots/01..09` (inicial, pagina completa, escena inicial, orbita, zoom con etiquetas solapadas, tras clic, oscuro desktop, oscuro movil, claro movil).
- Fixture: `fixture/gen.py`, `fixture/rich.jsonl`. Wireframes: `wireframes/`.
