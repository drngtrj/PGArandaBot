import os
import logging
from io import BytesIO
from PIL import Image
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram import BotCommand

# ---------------- Configuración ----------------
HF_API_KEY = os.environ["HF_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # opcional si vas a webhook

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Datos ----------------
# Diccionario de eventos -> lista de datos guardados
eventos = {}

# Variable para saber con qué evento estamos trabajando
evento_actual = None

# ---------------- Funciones HF ----------------
def enviar_a_hf(texto=None, imagen_bytes=None):
    """
    Envía texto o imagen a Hugging Face Inference API.
    """
    url = "https://router.huggingface.co/models/gpt-4o-mini"
    payload = {}

    if texto:
        payload["inputs"] = texto
    elif imagen_bytes:
        files = {"image": ("image.png", imagen_bytes)}
        response = requests.post(url, headers=HEADERS, files=files, timeout=30)
        if response.status_code != 200:
            return f"Error IA: {response.json()}"
        return response.json().get("generated_text", "No se pudo generar texto de la imagen.")
    else:
        return "No hay datos para procesar."

    response = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    if response.status_code != 200:
        return f"Error IA: {response.json()}"
    return response.json().get("generated_text", "No se pudo generar respuesta.")


# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy tu bot. Primero crea o selecciona un evento usando /evento <nombre_evento>."
    )

async def crear_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global evento_actual
    if not context.args:
        await update.message.reply_text("Debes poner un nombre de evento: /evento NombreDelEvento")
        return
    nombre_evento = " ".join(context.args)
    if nombre_evento not in eventos:
        eventos[nombre_evento] = []
    evento_actual = nombre_evento
    await update.message.reply_text(f"Evento seleccionado: {evento_actual}")

async def mostrar_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not eventos:
        await update.message.reply_text("No hay eventos creados todavía.")
        return
    teclado = [
        [InlineKeyboardButton(nombre, callback_data=nombre)] for nombre in eventos.keys()
    ]
    reply_markup = InlineKeyboardMarkup(teclado)
    await update.message.reply_text("Selecciona un evento:", reply_markup=reply_markup)

async def seleccionar_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global evento_actual
    query = update.callback_query
    await query.answer()
    evento_actual = query.data
    await query.edit_message_text(text=f"Evento seleccionado: {evento_actual}")

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global evento_actual
    if evento_actual is None:
        await update.message.reply_text("Primero selecciona un evento con /evento o /menu")
        return

    if update.message.photo:
        # Procesar imagen
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        resultado = enviar_a_hf(imagen_bytes=photo_bytes)
        eventos[evento_actual].append({"tipo": "imagen", "contenido": resultado})
        await update.message.reply_text(f"Procesé la imagen para el evento {evento_actual}:\n{resultado}")
    else:
        texto = update.message.text
        resultado = enviar_a_hf(texto=texto)
        eventos[evento_actual].append({"tipo": "texto", "contenido": resultado})
        await update.message.reply_text(f"Procesé el texto para el evento {evento_actual}:\n{resultado}")

async def listar_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if evento_actual is None:
        await update.message.reply_text("Primero selecciona un evento con /evento o /menu")
        return
    datos = eventos.get(evento_actual, [])
    if not datos:
        await update.message.reply_text(f"No hay datos guardados para el evento {evento_actual}")
        return
    mensaje = "\n\n".join([f"{i+1}. [{d['tipo']}] {d['contenido']}" for i, d in enumerate(datos)])
    await update.message.reply_text(f"Datos del evento {evento_actual}:\n{mensaje}")

# ---------------- Main ----------------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Comandos
comandos = [
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("evento", crear_evento))
    app.add_handler(CommandHandler("menu", mostrar_eventos))
    app.add_handler(CommandHandler("datos", listar_datos))
]
# Registrar comandos en Telegram
app.bot.set_my_commands(comandos)

# Callbacks
app.add_handler(CallbackQueryHandler(seleccionar_evento))

# Mensajes
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, manejar_mensaje))

# ---------------- Run ----------------
if __name__ == "__main__":
    # Para polling
    print("Bot listo")
    app.run_polling()
    
    # Para webhook, descomenta esto:
    # app.run_webhook(
    #     listen="0.0.0.0",
    #     port=int(os.environ.get("PORT", 8000)),
    #     webhook_url=WEBHOOK_URL
    # )



