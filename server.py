from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os

app = FastAPI()

# Crear carpeta para uploads si no existe
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Puerto de tu frontend
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,        
)

# -----------------------
# Endpoint de subida de archivos
# -----------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    print(f"[UPLOAD] Archivo recibido: {file.filename}")
    return {"filename": file.filename, "message": "Archivo subido correctamente"}

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

    if data.full_name == "Hildegard":
        return 0
    elif data.full_name == "Kariane":
        return 1
    
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
