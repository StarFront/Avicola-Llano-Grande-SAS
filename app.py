import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from connection import huevos_collection,ventas_collection


app = Flask(__name__)

PRECIOS = {
    "ROJO": {"A": 12000, "AA": 13500, "B": 11000, "EXTRA": 15000},
    "BLANCO": {"A": 10000, "AA": 11500, "B": 9500, "EXTRA": 14000}
}

@app.route('/')
def home():
    total_ventas = ventas_collection.count_documents({}) 
    return render_template("index.html", total_ventas=total_ventas)  

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

    ventas_collection.insert_one({
        "cliente": cliente,
        "documento": documento,
        "tipo_cliente": tipo_cliente,
        "tipo": tipo,
        "tamaño": tamaño,
        "unidad": unidad,
        "cantidad": cantidad,
        "fecha": datetime.now()
    })
    # Crear factura
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"factura_{cliente.replace(' ', '_')}_{timestamp}.txt"
    ruta_factura = os.path.join("facturas", nombre_archivo)

    os.makedirs("facturas", exist_ok=True)

    with open(ruta_factura, "w", encoding="utf-8") as f:
        logo_gallina = [
            "       .==;=.",
            "      / _  _ \\",
            "     |  o  o  |",
            "     \\   /\\   /             ,",
            "    ,/'-=\\/=-'\\,    |\\   /\\/ \\/|   ,_",
            "   / /        \\ \\   ; \\/     '; , \\_'_,",
            "  | /          \\ |   \\        /",
            "  \\/ \\        / \\/    '.    .'    /.",
            "      '.    .'          ~~ , /\\ `",
            "      _|~~|_              .",
            "      /|\\  /|\\"
        ]

        logo_huevo = [
            "       .==;=.",
            "      / _  _ \\",
            "     |  o  o  |",
            "     \\   /\\   /             ,",
            "    ,/'-=\\/=-'\\,    |\\   /\\/ \\/|   ,_",
            "   / /        \\ \\   ; \\/     '; , \\_'_,",
            "  | /          \\ |   \\        /",
            "  \\/ \\        / \\/    '.    .'    /.",
            "      '.    .'          ~~ , /\\ `",
            "      _|~~|_              .",
            "      /|\\  /|\\"
        ]
        f.write("\n")
        for izquierda, derecha in zip(logo_gallina, logo_huevo):
            linea = izquierda.ljust(60) + derecha + "\n"
            f.write(linea)

        f.write("\t\t\t\t\tGRANJA AVÍCOLA LLANO GRANDE S.A.S\n")
        f.write("\t\t\t\t\tNIT: 870545489-0\n")
        f.write("\t\t\t\t\tFACTURA DE VENTA\n")
        f.write(f"\t\t\t\t\tCliente: {cliente}\n")
        f.write(f"\t\t\t\t\tDocumento: {documento}\n")
        f.write(f"\t\t\t\t\tArtículo: {cantidad} {unidad.lower()}(s) de huevo {tipo} tamaño {tamaño}\n")
        f.write(f"\t\t\t\t\tSubtotal: ${subtotal}\n")
        f.write(f"\t\t\t\t\tIVA (5%): ${iva}\n")
        f.write(f"\t\t\t\t\tTotal a pagar: ${total}\n")
    
    return jsonify({"mensaje": f"Venta realizada con éxito. Factura generada: {nombre_archivo}"}), 200


if __name__ == '__main__':
    app.run(debug=True)
