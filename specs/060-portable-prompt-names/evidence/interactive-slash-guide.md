# SPEC-060: guía para observar el menú de slash interactivo (pendiente de resultado del propietario)

Estado: **PENDIENTE**. Esta guía no contiene ninguna observación interactiva; la parte C
del addendum [native-observation-0.1.0a2-addendum.md](native-observation-0.1.0a2-addendum.md)
queda abierta hasta que el propietario pegue el resultado. Nada de lo que sigue autoriza una
release, una etiqueta ni una publicación, y no cierra por sí misma la tarea T009.

Qué pregunta responde: la documentación (`docs/tooling/INSTALL.md`, `docs/tooling/NATIVE_PLUGINS.md`)
afirma que, con el servidor portátil registrado bajo la clave `agent-braid` junto al plugin
nativo, el prompt `analyze` se vería como `/agent-braid:analyze (MCP)` y compartiría nombre con la
skill `/agent-braid:analyze`. La observación 0.1.0a2 solo leyó el registro interno (`mcp__agent-braid__analyze`
junto a la skill `agent-braid:analyze`: cadenas distintas, sin duplicado) y no cómo lo dibuja el menú.

Versiones de referencia: Claude Code 2.1.292, paquete `agent-braid` 0.1.0a2 con el extra `tooling`
(`mcp==2.3.0`), plugin nativo `0.1.0-alpha.4`. Otras versiones pueden pintar el menú de otra forma;
anótala.

Los pasos 1 a 3 se ejecutaron sin interfaz en un perfil desechable hasta `claude mcp list` (ambos
servidores Connected) y hasta el registro de comandos del registro `init` (seis skills `agent-braid:*` y seis
`mcp__agent-braid__*`). El menú interactivo en sí no se abrió.

## Precauciones

- Abrir el menú (`/`) y escribir para filtrar **no envía nada al modelo**. **No pulses Intro sobre una
  entrada del menú**: ejecutar un prompt MCP sí lo envía como mensaje a una sesión con modelo.
  Cierra el menú con `Esc` y sal con `Ctrl+C` dos veces.
- Usa un perfil desechable para no tocar tu configuración real. Necesitará un inicio de sesión
  propio de Claude Code (es lo único que no puede hacer un agente); si prefieres tu perfil real,
  retira las entradas al terminar (paso 5).
- Si el servidor del plugin aparece como `failed` en `/mcp` justo tras un intento fallido, borra
  `$CLAUDE_CONFIG_DIR/mcp-needs-auth-cache.json` o espera unos 15 minutos antes de repetir: es una
  caché de fallos de Claude Code, no un fallo del plugin (ver el addendum, parte A).

## Los 5 pasos

1. **Perfil y paquete.** Crea un directorio privado y un entorno con Python 3.12 o superior:

   ```sh
   export OBS=$(mktemp -d) && chmod 700 "$OBS"
   python3 -m venv "$OBS/venv"
   "$OBS/venv/bin/python" -m pip install '/ruta/absoluta/agent_braid-0.1.0a2-py3-none-any.whl[tooling]'
   mkdir -p "$OBS/claude" "$OBS/home" "$OBS/results" "$OBS/ab-home" "$OBS/repo"
   chmod 700 "$OBS/ab-home" && git -C "$OBS/repo" init -q
   export CLAUDE_CONFIG_DIR="$OBS/claude" AGENT_BRAID_HOME="$OBS/ab-home"
   ```

   Usa el wheel que tengas del candidato 0.1.0a2 (el construido desde `develop`). Todas las rutas
   deben ser canónicas, sin enlaces simbólicos ni `..` (si `$TMPDIR` pasa por un symlink, usa `cd -P`
   o `realpath`).

2. **Plugin nativo alpha.4 y su `setup`.** Instala el plugin desde su marketplace y registra el
   repositorio de prueba (la vista previa pide un resumen y luego repetir con el resumen exacto):

   ```sh
   claude plugin marketplace add https://github.com/jayanez/agent-braid.git#agent-braid--v0.1.0-alpha.4
   claude plugin install agent-braid@agent-braid --scope user
   LAUNCH="$CLAUDE_CONFIG_DIR/plugins/cache/agent-braid/agent-braid/0.1.0-alpha.4/launch"
   "$LAUNCH" plugin setup --source-root "$OBS/repo"           # anota previewDigest
   "$LAUNCH" plugin setup --source-root "$OBS/repo" --apply --preview-digest EL_DIGEST
   ```

   Si la ruta de `$LAUNCH` no existe, localízala con `claude plugin list` o `find "$CLAUDE_CONFIG_DIR/plugins" -name launch`.

3. **Caso A: portátil bajo la clave `agent-braid` (colisión).**

   ```sh
   claude mcp add agent-braid --scope user -- "$OBS/venv/bin/agent-braid" tooling serve \
     --source-root "$OBS/repo" --result-root "$OBS/results"
   claude mcp list        # esperado: plugin:agent-braid:agent-braid y agent-braid, ambos Connected
   claude                 # sesión interactiva; escribe "/" y luego "analyze", "agent-braid" y "evidence"
   ```

   Observa el menú con el filtro vacío (`/`) y con cada filtro. No pulses Intro sobre ninguna entrada.

4. **Caso B: portátil bajo otra clave** (por ejemplo `portable-braid`), con el plugin aún instalado:

   ```sh
   claude mcp remove agent-braid --scope user
   claude mcp add portable-braid --scope user -- "$OBS/venv/bin/agent-braid" tooling serve \
     --source-root "$OBS/repo" --result-root "$OBS/results"
   claude
   ```

   Repite exactamente los mismos filtros que en el paso 3. Opcional: repite también con el plugin
   desinstalado (`claude plugin uninstall agent-braid@agent-braid`) y solo el portátil.

5. **Qué anotar y limpieza.** Para cada caso anota, con captura de pantalla si puedes:

   - Cómo se muestra cada una de las seis entradas del portátil: `analyze`, `plan`, `evidence`,
     `agent-braid-analyze`, `agent-braid-plan`, `agent-braid-evidence`. Forma exacta del nombre
     (`/analyze`, `/mcp__agent-braid__analyze`, `/agent-braid:analyze`, `/portable-braid:analyze`,
     `agent-braid-analyze`...) y si lleva el sufijo `(MCP)`.
   - Cómo se muestran las seis skills del plugin (`agent-braid:analyze`, `:plan`, `:evidence`,
     `:execute`, `:recover`, `:setup`).
   - **Duplicados**: si dos entradas se dibujan con el mismo texto, si una oculta a la otra, si el
     menú avisa de un conflicto y qué entrada se selecciona (resalta, no ejecutes) al filtrar `agent-braid:analyze`.
   - Si las tres entradas `agent-braid-*` se distinguen como obsoletas (la descripción empieza por
     "Deprecated alias of ...") y si la descripción se ve en el menú.
   - Versión de Claude Code (`claude --version`), sistema operativo y el resultado de `claude mcp list`.

   Limpieza: sal con `Ctrl+C`, ejecuta `claude mcp remove portable-braid --scope user` (y `agent-braid` si
   quedó), `claude plugin uninstall agent-braid@agent-braid` y borra `$OBS`.

## Plantilla de resultado (pegar de vuelta)

```text
SPEC-060 interactive slash observation (owner result)
Fecha / quién:
Claude Code: <version>   SO: <sistema>   paquete: 0.1.0a2   plugin: 0.1.0-alpha.4
Perfil: desechable (CLAUDE_CONFIG_DIR=...) / real
claude mcp list (caso A): ...
claude mcp list (caso B): ...

CASO A (portátil bajo la clave "agent-braid" + plugin)
  /analyze            -> aparece como: ........  sufijo (MCP): sí/no
  agent-braid-analyze -> aparece como: ........  sufijo (MCP): sí/no  marcado obsoleto: sí/no
  agent-braid:analyze -> aparece como: ........  (skill del plugin)  ¿una o dos entradas?: ...
  plan / evidence (+ alias): ........
  Duplicados o aviso de conflicto: sí/no -> descripción: ........
  Al filtrar "agent-braid:analyze" se resalta: ........

CASO B (portátil bajo otra clave: ........)
  analyze -> ........  sufijo (MCP): sí/no
  agent-braid-analyze -> ........  marcado obsoleto: sí/no
  plan / evidence (+ alias): ........
  Duplicados o aviso de conflicto: sí/no -> ........

Descripciones visibles en el menú: sí/no  (texto: ........)
Capturas adjuntas: sí/no
¿Confirma o refuta el aviso de colisión de INSTALL.md y NATIVE_PLUGINS.md? confirma / refuta / parcial
Nada se ejecutó con Intro sobre una entrada del menú: sí/no
Otras observaciones: ........
```

Con el resultado pegado, un agente actualizará este archivo y el addendum (parte C) y, si el
aviso de colisión de la documentación cambia, corregirá `INSTALL.md` y `NATIVE_PLUGINS.md` en el
mismo cambio. Hasta entonces la advertencia de colisión sigue **sin confirmar ni refutar**.
