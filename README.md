# Fama · Sofá en salón (IA)

## Qué hace
1. Pegas la URL de un presupuesto (ej. `https://famav4.sim3d.es/#/order/...`).
2. El backend abre esa página con un navegador headless (Playwright), localiza
   automáticamente la imagen/render más grande de la pantalla y la recorta.
3. Envía ese recorte a Gemini (`gemini-2.5-flash-image`) con un prompt fijo
   que integra el sofá en un salón realista.
4. Devuelve la imagen generada al navegador.

## Desplegar en Render.com (recomendado, soporta Docker gratis)
1. Sube esta carpeta a un repo de GitHub.
2. En Render: **New > Web Service** → conecta el repo → Render detecta el `Dockerfile` solo.
3. En **Environment**, añade la variable:
   - `GEMINI_API_KEY` = tu clave de https://aistudio.google.com/apikey
4. (Opcional) Para proteger la web con usuario/contraseña, añade también:
   - `APP_USER` = el usuario que quieras (ej. `fama`)
   - `APP_PASSWORD` = la contraseña que quieras
   Si no añades estas dos, la web queda abierta sin login. Para cambiar la
   contraseña más adelante, solo edita `APP_PASSWORD` en esta misma sección
   de Render — no hace falta tocar código ni volver a desplegar manualmente,
   Render reinicia el servicio solo al guardar la variable.
5. Deploy. Render te da una URL pública (`https://tu-app.onrender.com`).

## Probar en local
```bash
pip install -r requirements.txt
playwright install chromium --with-deps
export GEMINI_API_KEY=tu_clave
uvicorn main:app --reload
```
Abre http://localhost:8000

## Aviso importante
La captura de la imagen del presupuesto depende de que la página sea
accesible sin login. Si `famav4.sim3d.es` requiere sesión iniciada, esta
técnica no podrá leerla — habría que investigar si existe una API interna
que devuelva directamente la URL de la imagen del render (más fiable que
hacer capturas de pantalla). Si me pasas una URL de presupuesto que
funcione sin iniciar sesión, puedo revisar si el enfoque de captura de
pantalla identifica bien el sofá o si hay que ajustar el selector.
