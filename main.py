import base64
import io
import os

from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from playwright.async_api import async_playwright
from PIL import Image
from google import genai

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT_BASE = (
    "Integra este sofá exactamente como aparece en la imagen "
    "(mismo color, forma y cojines) dentro de {escena}, "
    "con una perspectiva realista, como si fuera una foto de catálogo de interiorismo."
)

ESCENA_DEFECTO = "un salón moderno y luminoso, con iluminación natural y decoración minimalista"

INSTRUCCION_PLANO = (
    " Usa la imagen adicional del plano del salón como referencia de proporciones, "
    "medidas, y ubicación de puertas y ventanas: respeta esa distribución al componer la escena."
)


def construir_prompt(descripcion_usuario: str | None, hay_plano: bool) -> str:
    escena = descripcion_usuario.strip() if descripcion_usuario and descripcion_usuario.strip() else ESCENA_DEFECTO
    prompt = PROMPT_BASE.format(escena=escena)
    if hay_plano:
        prompt += INSTRUCCION_PLANO
    return prompt


async def capturar_imagen_producto(url: str) -> bytes:
    """Abre la URL del presupuesto y recorta la imagen/canvas más grande de la página."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1600, "height": 1200})
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # Dar tiempo a que el visor 3D/imagen termine de renderizar
        await page.wait_for_timeout(2500)

        candidatos = await page.evaluate(
            """
            () => {
                const els = [...document.querySelectorAll('img, canvas')];
                return els.map((el, i) => {
                    const r = el.getBoundingClientRect();
                    return { i, area: r.width * r.height, x: r.x, y: r.y, w: r.width, h: r.height };
                }).filter(e => e.w > 50 && e.h > 50);
            }
            """
        )
        if not candidatos:
            await browser.close()
            raise ValueError("No se encontró ninguna imagen o render en la página")

        mejor = max(candidatos, key=lambda c: c["area"])
        clip = {"x": mejor["x"], "y": mejor["y"], "width": mejor["w"], "height": mejor["h"]}

        screenshot_bytes = await page.screenshot(clip=clip)
        await browser.close()
        return screenshot_bytes


def generar_imagen_salon(imagen_bytes: bytes, prompt: str, plano_bytes: bytes | None = None) -> bytes:
    imagen_sofa = Image.open(io.BytesIO(imagen_bytes))
    contenido = [imagen_sofa, prompt]
    if plano_bytes:
        contenido.insert(1, Image.open(io.BytesIO(plano_bytes)))

    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=contenido,
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return part.inline_data.data

    raise ValueError("Gemini no devolvió ninguna imagen")


@app.post("/generar")
async def generar(
    url: str = Form(...),
    prompt: str | None = Form(None),
    plano: UploadFile | None = File(None),
):
    try:
        producto_bytes = await capturar_imagen_producto(url)
        plano_bytes = await plano.read() if plano is not None and plano.filename else None
        resultado_bytes = generar_imagen_salon(
            producto_bytes, construir_prompt(prompt, hay_plano=plano_bytes is not None), plano_bytes
        )
        return JSONResponse({
            "imagen_base64": base64.b64encode(resultado_bytes).decode("utf-8"),
            "recorte_original_base64": base64.b64encode(producto_bytes).decode("utf-8"),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/", StaticFiles(directory="static", html=True), name="static")
