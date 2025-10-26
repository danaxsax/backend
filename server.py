from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
from pipeline import procesar_documentos_usuario

app = FastAPI()

# Crear carpeta para uploads si no existe
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://hack-mty2025.vercel.app", "http://hack-mty2025.vercel.app"],  # Puerto de tu frontend
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,        
)


class AnalysisRequest(BaseModel):
    fullName: str

@app.post("/analysis")
async def analyze_file(request: AnalysisRequest):
    try:
        # Mapeo de nombres a nombres en la base de datos
        nombre_map = {
            "cyrce": "Cyrce D Salinas Rojas",
            "hildegard": "Hildegard Zerrweck"
        }
        
        # Normalizar el nombre recibido
        nombre_normalizado = request.fullName.lower().strip()
        
        # Buscar coincidencia parcial
        nombre_usuario = None
        for key, value in nombre_map.items():
            if key in nombre_normalizado or nombre_normalizado in key:
                nombre_usuario = value
                break
        
        # Si no hay coincidencia, intentar buscar directamente
        if not nombre_usuario:
            nombre_usuario = request.fullName
        
        print(f"[ANALYSIS] Procesando para usuario: {nombre_usuario}")
        
        # Procesar el archivo y generar el perfil + retroalimentación
        resultado = procesar_documentos_usuario(name_user=nombre_usuario)
        
        return {
            "message": "Análisis completado",
            "perfil": resultado["perfil"],
            "retroalimentacion": resultado["retroalimentacion"],
            "detalle_tarjetas": resultado["detalle_tarjetas"]
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=f"Usuario no encontrado: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar archivo: {str(e)}")
# -----------------------
# Endpoint de subida de archivos
# -----------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Guardar el archivo
        file_location = f"{UPLOAD_DIR}/{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"[UPLOAD] Archivo recibido: {file.filename}")
        
        # Procesar el archivo y generar el perfil + retroalimentación
        resultado = procesar_documentos_usuario(file_location)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")

# -----------------------
# Endpoint de autenticación
# -----------------------
@app.post("/auth/register")
async def auth_register(request: Request):
    data = await request.json()
    print("[AUTH REGISTER] Datos recibidos:", data)
    return {"message": "Registro recibido", "data": data}

@app.post("/auth/login")
async def auth_login(request: Request):
    data = await request.json()
    print("[AUTH LOGIN] Datos recibidos:", data)
    return {"message": "Login recibido", "data": data}

# -----------------------
# Endpoint de perfil de usuario
# -----------------------
@app.post("/user/profile")
async def user_profile(request: Request):
    data = await request.json()
    print("[USER PROFILE] Datos recibidos:", data)

    return {"message": "Perfil de usuario recibido", "data": data}

# -----------------------
# Endpoints de tarjetas
# -----------------------
@app.post("/cards")
async def add_card(request: Request):
    data = await request.json()
    print("[ADD CARD] Datos recibidos:", data)
    return {"message": "Tarjeta recibida", "data": data}

@app.put("/cards/{card_id}")
async def update_card(card_id: str, request: Request):
    data = await request.json()
    print(f"[UPDATE CARD] ID: {card_id}, Datos recibidos:", data)
    return {"message": f"Tarjeta {card_id} actualizada", "data": data}

@app.delete("/cards/{card_id}")
async def delete_card(card_id: str):
    print(f"[DELETE CARD] ID: {card_id} - solicitud de borrado")
    return {"message": f"Tarjeta {card_id} borrada"}