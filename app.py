import os
from datetime import datetime
from flask import Response
from flask import Flask, request, jsonify, render_template
from connection import huevos_collection


app = Flask(__name__)

PRECIOS = {
    "ROJO": {"A": 12000, "AA": 13500, "B": 11000, "EXTRA": 15000},
    "BLANCO": {"A": 10000, "AA": 11500, "B": 9500, "EXTRA": 14000}
}

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/registro')
def registro():
    return render_template('registro.html')

@app.route('/registrar_huevos', methods=['POST'])
def registrar_huevos():
    data = request.json
    tipo = data.get("tipo")
    tamaño = data.get("tamaño")
    cubetas = int(data.get("cantidad_cubetas", 0))

    if tipo not in PRECIOS or tamaño not in PRECIOS[tipo]:
        return jsonify({"error": "Tipo o tamaño inválido"}), 400

    unidades = cubetas * 30
    precio_cubeta = PRECIOS[tipo][tamaño]
    precio_docena = round((precio_cubeta / 30) * 12)

    filtro = {"tipo": tipo, "tamaño": tamaño}
    existente = huevos_collection.find_one(filtro)

    if existente:
        nuevo_stock = existente["stock_unidades"] + unidades
        huevos_collection.update_one(filtro, {
            "$set": {"stock_unidades": nuevo_stock}
        })
    else:
        huevos_collection.insert_one({
            "tipo": tipo,
            "tamaño": tamaño,
            "stock_unidades": unidades,
            "precio_cubeta": precio_cubeta,
            "precio_docena": precio_docena
        })

    return jsonify({"mensaje": "Huevos registrados correctamente"}), 200

import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from connection import huevos_collection


@app.route('/venta')
def venta():
    return render_template('venta.html')


@app.route('/vender_huevos', methods=['POST'])
def vender_huevos():
    data = request.json
    cliente = data.get("cliente")
    documento = data.get("documento")
    tipo_cliente = data.get("tipo_cliente")
    tipo = data.get("tipo")
    tamaño = data.get("tamaño")
    unidad = data.get("unidad")
    cantidad = int(data.get("cantidad"))

    if tipo not in PRECIOS or tamaño not in PRECIOS[tipo]:
        return jsonify({"mensaje": "Tipo o tamaño inválido"}), 400

    # Validación de tipo de cliente
    if tipo_cliente == "JURIDICO" and unidad == "DOCENA":
        return jsonify({"mensaje": "Clientes jurídicos solo pueden comprar por cubeta"}), 400

    # Determinar cantidad de unidades a vender
    if unidad == "CUBETA":
        unidades = cantidad * 30
        precio_unitario = PRECIOS[tipo][tamaño]
    else:  # DOCENA
        unidades = cantidad * 12
        precio_unitario = round((PRECIOS[tipo][tamaño] / 30) * 12)

    # Verificar stock
    filtro = {"tipo": tipo, "tamaño": tamaño}
    existente = huevos_collection.find_one(filtro)

    if not existente or existente["stock_unidades"] < unidades:
        return jsonify({"mensaje": "Stock insuficiente para esta venta"}), 400

    # Calcular totales
    subtotal = precio_unitario * cantidad
    iva = round(subtotal * 0.05)
    total = subtotal + iva

    # Actualizar stock
    nuevo_stock = existente["stock_unidades"] - unidades
    huevos_collection.update_one(filtro, {"$set": {"stock_unidades": nuevo_stock}})

    # Crear factura en memoria
    factura_lines = []
    factura_lines.append(f"Factura de venta - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    factura_lines.append(f"Cliente: {cliente}\n")
    factura_lines.append(f"Documento: {documento}\n")
    factura_lines.append(f"Tipo de cliente: {tipo_cliente}\n")
    factura_lines.append(f"Artículo: {cantidad} {unidad.lower()}(s) de huevo {tipo} tamaño {tamaño}\n")
    factura_lines.append(f"Subtotal: ${subtotal}\n")
    factura_lines.append(f"IVA (5%): ${iva}\n")
    factura_lines.append(f"Total a pagar: ${total}\n")
    print(data)
    # Devolver factura como respuesta para descarga
    content = "\n".join(factura_lines)
    return Response(content, mimetype='text/plain', headers={
        'Content-Disposition': f'attachment; filename=factura_{cliente.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render usa esta variable
    app.run(host='0.0.0.0', port=port)
