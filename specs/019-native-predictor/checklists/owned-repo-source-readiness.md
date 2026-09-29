# Revisión de preparación de fuentes de repositorios propios

Estado: **pendiente**. Esta lista evalúa si una fuente puede entrar en una
auditoría de eventos; no autoriza acceso, captura, corpus ni entrenamiento.

## Por fuente y flujo

- [x] La pantalla inicial se limitó a arquitectura, esquemas, specs y docs.
- [x] Kinetiq se limita a flujos no clínicos de autoría; se excluyen vídeo,
  keypoints, biometría y material de atletas/clientes.
- [x] SmartNotes se limita a autoría documental no clínica; se excluyen
  pacientes, `PA-NNNN`, datos clínicos, actividad STT, audio y transcripciones.
- [x] Los commits, diffs, Issues y trazas de procesamiento no se tratan como
  eventos concurrentes de inserción.
- [ ] Responsable del feed y autorización de captura optativa identificados.
- [ ] Derechos y privacidad revisados antes de abrir cualquier registro.
- [ ] Feed inmutable con base compartida, operaciones, anclas y procedencia
  documentado y probado para completitud.
- [ ] Ventana contigua y regla de muestreo congeladas antes de inspeccionar
  eventos candidatos.
- [ ] Todas las sesiones y parejas enumeradas, con exclusiones por causa.
- [ ] Adaptador validado contra `anchored-sequence-v1` sin reconstrucción ni
  recorte de sesiones.
- [ ] Revisión de salida confirma que no se publica contenido privado ni datos
  que permitan recuperar contenido.

## Resultado actual

El inventario encontró **0 sesiones reales y 0 pares elegibles** en cada uno
de los dos repositorios. Son recuentos de la pantalla estructural, no de una
ventana de captura ni una estimación de rendimiento. No se ha abierto ningún
registro real. P019-01 y T001 permanecen abiertos; no entrenar ni calibrar.
