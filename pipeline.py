# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Bases de datos (en producción estas vendrían de una BD real)
database_banco = pd.DataFrame([
    {"banco":"BANAMEX","tipo_tarjeta":"TDC","nombre_Tarjeta":"COSTCO","id_Tarjeta":1,"tasa_Interes":61.9},
    {"banco":"BBVA","tipo_tarjeta":"TDC","nombre_Tarjeta":"AZUL","id_Tarjeta":2,"tasa_Interes":50.56},
    {"banco":"KLAR","tipo_tarjeta":"TDC","nombre_Tarjeta":"KLAR","id_Tarjeta":3,"tasa_Interes":123.0},
])

database_user = pd.DataFrame([
    {"Nombre":"Cyrce D Salinas Rojas","banco":"BANAMEX","Id_TDC":1,"saldo_deudor_total":2527.41,"credito_disponible":7473.0,"limite_credito":10000.0,
     "dia_corte":16,"dia_limite_pago":5,"num_dias_periodo":30,"pago_minimo_msi":390.0,"pago_no_generar_intereses":2527.41,
     "pago_minimo":390.0,"saldo_compras_msi":0.0,"CAT":89.5},
    {"Nombre":"Hildegard Zerrweck","banco":"BBVA","Id_TDC":2,"saldo_deudor_total":7261.44,"credito_disponible":38.56,"limite_credito":7300.0,
     "dia_corte":19,"dia_limite_pago":10,"num_dias_periodo":30,"pago_minimo_msi":2006.0,"pago_no_generar_intereses":2702.0,
     "pago_minimo":250.0,"saldo_compras_msi":1756.0,"CAT":12.2},
    {"Nombre":"Hildegard Zerrweck","banco":"KLAR","Id_TDC":3,"saldo_deudor_total":3994.63,"credito_disponible":5.37,"limite_credito":4000.0,
     "dia_corte":14,"dia_limite_pago":24,"num_dias_periodo":31,"pago_minimo_msi":550.86,"pago_no_generar_intereses":3843.17,
     "pago_minimo":399.59,"saldo_compras_msi":151.27,"CAT":187.0},
])

def build_public_lookup(db_banco: pd.DataFrame):
    """
    Construye mapas públicos de solo-lectura:
      - rate_map[(banco, id_tarjeta)] -> tasa anual decimal
      - name_map[(banco, id_tarjeta)] -> nombre de la tarjeta
    """
    rate_map, name_map = {}, {}
    for _, row in db_banco.iterrows():
        key = (row["banco"], int(row["id_Tarjeta"]))
        rate_map[key] = float(row["tasa_Interes"]) / 100.0
        name_map[key] = str(row["nombre_Tarjeta"])
    return rate_map, name_map

def plan_pagos_usuario(
    df_user: pd.DataFrame,
    rate_map: dict,
    name_map: dict,
    presupuesto_total: float = 10000.0,
    reserva_frac: float = 0.30,
    evitar_prepago_msi: bool = True,
    u_star: float = None,
    lambda_util: float = 0.0,
):
    """
    Minimiza:  sum_i phi_i * max(0, PNI_i - p_i)
    s.a.:
      - sum_i p_i <= P_pagable = presupuesto_total * (1 - reserva_frac)
      - p_i >= minimo_requerido = max(pago_minimo, pago_minimo_msi)
      - p_i <= saldo y (opcional) no prepagos MSI (tope: min_req + (saldo - MSI))
    Estrategia greedy óptima: cubrir mínimos y asignar extra por mayor 'phi' hasta PNI.
    """
    P_pagable = max(0.0, float(presupuesto_total) * (1.0 - float(reserva_frac)))
    reserva_objetivo = float(presupuesto_total) - P_pagable

    filas = []
    for _, r in df_user.iterrows():
        key = (r["banco"], int(r["Id_TDC"]))
        A = float(rate_map.get(key, 0.0))
        nombre_tarjeta = name_map.get(key, f"TDC_{r['Id_TDC']}")
        dias = int(r.get("num_dias_periodo", 30))
        phi = (1.0 + A/365.0)**dias - 1.0

        saldo  = float(r["saldo_deudor_total"])
        limite = float(r["limite_credito"])
        min_plain = float(r.get("pago_minimo", 0.0))
        min_msi   = float(r.get("pago_minimo_msi", 0.0))
        min_req   = max(min_plain, min_msi)
        pni       = float(r.get("pago_no_generar_intereses", min_req))
        pni       = max(pni, min_req)
        msi_saldo = float(r.get("saldo_compras_msi", 0.0))

        if evitar_prepago_msi:
            extra_max = max(0.0, saldo - msi_saldo)
        else:
            extra_max = max(0.0, saldo - min_req)

        pago_max = min(saldo, min_req + extra_max)

        filas.append({
            "Nombre": r["Nombre"],
            "banco": r["banco"],
            "Id_TDC": int(r["Id_TDC"]),
            "Tarjeta": nombre_tarjeta,
            "tasa_Interes": A * 100.0,
            "phi": phi,
            "saldo": saldo,
            "limite": limite,
            "min_req": min_req,
            "PNI": pni,
            "pago_max": pago_max
        })

    work = pd.DataFrame(filas)
    if work.empty:
        return work, {
            "presupuesto_total": presupuesto_total,
            "reserva_objetivo": reserva_objetivo,
            "presupuesto_pagable": P_pagable,
            "pagos_totales": 0.0,
            "reserva_guardada_real": presupuesto_total,
            "interes_total_estimado": 0.0
        }

    work["Pago"] = work["min_req"].astype(float)
    suma_minimos = float(work["Pago"].sum())

    if suma_minimos <= P_pagable:
        P_rest = P_pagable - suma_minimos
    else:
        ratio = P_pagable / suma_minimos if suma_minimos > 0 else 0.0
        work["Pago"] = work["min_req"] * ratio
        P_rest = 0.0

    work["gap_pni"]   = (work["PNI"] - work["Pago"]).clip(lower=0.0)
    work["extra_cap"] = (work["pago_max"] - work["Pago"]).clip(lower=0.0)
    work["extra_obj"] = work[["gap_pni", "extra_cap"]].min(axis=1)

    orden = list(work.sort_values("phi", ascending=False).index)
    for i in orden:
        if P_rest <= 0: break
        cap = float(work.at[i, "extra_obj"])
        if cap <= 0: continue
        asignar = min(cap, P_rest)
        work.at[i, "Pago"] += asignar
        P_rest -= asignar

    work["Interes_generado"] = work["phi"] * (work["PNI"] - work["Pago"]).clip(lower=0.0)
    work["coef_interes_periodo"] = work["phi"]
    work["min_requerido"] = work["min_req"]
    work["saldo_deudor_total"] = work["saldo"]
    work["limite_credito"] = work["limite"]
    work["utilizacion_inicial"] = (work["saldo"] / work["limite"]).replace([np.inf,-np.inf], np.nan)
    work["utilizacion_post"] = ((work["saldo"] - work["Pago"]) / work["limite"]).clip(lower=0.0)

    pagos_totales = float(work["Pago"].sum())
    reserva_guardada_real = float(presupuesto_total) - pagos_totales

    out = work[[
        "Nombre","Tarjeta","banco","Id_TDC","tasa_Interes",
        "Pago","Interes_generado","coef_interes_periodo","PNI","min_requerido",
        "saldo_deudor_total","limite_credito","utilizacion_inicial","utilizacion_post"
    ]].copy()

    out["presupuesto_total"]  = float(presupuesto_total)
    out["reserva_objetivo"]   = reserva_objetivo
    out["presupuesto_pagable"] = P_pagable
    out["reserva_guardada_real"] = reserva_guardada_real

    resumen = {
        "presupuesto_total": float(presupuesto_total),
        "reserva_objetivo": reserva_objetivo,
        "presupuesto_pagable": P_pagable,
        "pagos_totales": pagos_totales,
        "reserva_guardada_real": reserva_guardada_real,
        "interes_total_estimado": float(work["Interes_generado"].sum()),
    }
    return out, resumen

def generar_prompt_feedback(df_plan, nombre_usuario, presupuesto_total,
                            resumenes=None, reserva_frac_default=0.30):
    """
    Construye un prompt compacto con el plan de pagos del usuario y su presupuesto.
    """
    dfu = (df_plan[df_plan["Nombre"] == nombre_usuario]
           [['Tarjeta','banco','Id_TDC','Pago','Interes_generado','PNI','min_requerido',
             'saldo_deudor_total','limite_credito','utilizacion_inicial','utilizacion_post']]
           .copy())
    if dfu.empty:
        raise ValueError(f"No hay filas para '{nombre_usuario}' en df_plan.")

    pagos_totales = float(dfu['Pago'].sum())
    interes_total = float(dfu['Interes_generado'].sum())

    if resumenes and nombre_usuario in resumenes:
        presupuesto_pagable = float(resumenes[nombre_usuario].get('presupuesto_pagable',
                                   presupuesto_total*(1-reserva_frac_default)))
        reserva_objetivo    = float(resumenes[nombre_usuario].get('reserva_objetivo',
                                   presupuesto_total*reserva_frac_default))
    else:
        reserva_objetivo    = presupuesto_total*reserva_frac_default
        presupuesto_pagable = presupuesto_total - reserva_objetivo

    reserva_guardada_real = presupuesto_total - pagos_totales

    def fmt_pct(x):
        try: return f"{100*float(x):.1f}%"
        except: return "NA"

    lineas = []
    for _, r in dfu.sort_values('Pago', ascending=False).iterrows():
        lineas.append(
            f"- {r['Tarjeta']} ({r['banco']} #{int(r['Id_TDC'])}): "
            f"Pago ${float(r['Pago']):,.2f} | PNI ${float(r['PNI']):,.2f} | "
            f"Interés ciclo ${float(r['Interes_generado']):,.2f} | "
            f"Util {fmt_pct(r['utilizacion_inicial'])}→{fmt_pct(r['utilizacion_post'])}"
        )
    detalle_txt = "\n".join(lineas)

    prompt = f"""
Actúa como asesor financiero personal. Con base en el siguiente plan de pagos,
da retroalimentación en prosa, específica y accionable en español. Evita jerga.

Perfil:
- Usuario: {nombre_usuario}
- Presupuesto mensual total: ${presupuesto_total:,.2f}
- Reserva objetivo: ${reserva_objetivo:,.2f}
- Presupuesto asignable a tarjetas: ${presupuesto_pagable:,.2f}
- Pagos totales del plan: ${pagos_totales:,.2f}
- Reserva guardada real: ${reserva_guardada_real:,.2f}
- Interés estimado del ciclo: ${interes_total:,.2f}

Tarjetas:
{detalle_txt}

Instrucciones:
indica: si el plan evita intereses, qué tarjeta conviene priorizar
la siguiente quincena (di por qué), si alguna utilización (>30%) merece atención,
si conviene redondear pagos o ajustar mínimos.
recuerda que todo esto debe ir en prosa en un párrafo como si fueras una persona dando su retroalimentación al usuario.
"""
    return prompt.strip()

def procesar_documentos_usuario(name_user: str):
    """
    Función principal que procesa el archivo subido y genera el perfil completo + retroalimentación.
    
    Args:
        name_user: Nombre del usuario a procesar
        
    Returns:
        dict con perfil, retroalimentación y detalle de tarjetas
    """
    nombre_usuario = name_user
    presupuesto_total = 10000.0
    
    # Construir mapas de tasas y nombres
    rate_map, name_map = build_public_lookup(database_banco)
    
    # Filtrar datos del usuario
    df_usuario = database_user[database_user["Nombre"] == nombre_usuario]
    
    # Validar que el usuario existe
    if df_usuario.empty:
        raise ValueError(f"No se encontraron datos para el usuario: {nombre_usuario}")
    
    # Calcular plan de pagos
    df_plan, resumen = plan_pagos_usuario(
        df_usuario,
        rate_map,
        name_map,
        presupuesto_total=presupuesto_total,
        reserva_frac=0.30,
        evitar_prepago_msi=True
    )
    
    # Generar retroalimentación con Gemini
    client = genai.Client(api_key=GEMINI_API_KEY)
    MODEL_ID = "gemini-2.5-pro"
    
    prompt = generar_prompt_feedback(
        df_plan=df_plan,
        nombre_usuario=nombre_usuario,
        presupuesto_total=presupuesto_total,
        resumenes={nombre_usuario: resumen}
    )
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    
    # Preparar detalle de tarjetas
    detalle_tarjetas = []
    df_detalle = df_plan[df_plan["Nombre"] == nombre_usuario]
    for _, row in df_detalle.iterrows():
        detalle_tarjetas.append({
            "tarjeta": row["Tarjeta"],
            "banco": row["banco"],
            "id_tdc": int(row["Id_TDC"]),
            "pago": float(row["Pago"]),
            "interes_generado": float(row["Interes_generado"]),
            "pni": float(row["PNI"]),
            "saldo_total": float(row["saldo_deudor_total"]),
            "limite_credito": float(row["limite_credito"]),
            "utilizacion_inicial": f"{100*float(row['utilizacion_inicial']):.1f}%",
            "utilizacion_post": f"{100*float(row['utilizacion_post']):.1f}%"
        })
    
    # Construir respuesta completa
    return {
        "perfil": {
            "usuario": nombre_usuario,
            "presupuesto_mensual_total": f"${resumen['presupuesto_total']:,.2f}",
            "reserva_objetivo": f"${resumen['reserva_objetivo']:,.2f}",
            "presupuesto_asignable": f"${resumen['presupuesto_pagable']:,.2f}",
            "pagos_totales": f"${resumen['pagos_totales']:,.2f}",
            "reserva_guardada_real": f"${resumen['reserva_guardada_real']:,.2f}",
            "interes_estimado_ciclo": f"${resumen['interes_total_estimado']:,.2f}"
        },
        "retroalimentacion": response.text,
        "detalle_tarjetas": detalle_tarjetas
    }