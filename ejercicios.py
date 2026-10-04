from flask import Flask, render_template, request, session
import random
import uuid
from db import guardar, consultar

app = Flask(__name__)
app.secret_key = "clave-inventario"


@app.route("/", methods=["GET", "POST"])
def ejercicios():

    menu = request.args.get("menu", "parimpar")

    if "usuario_id" not in session:
        session["usuario_id"] = str(uuid.uuid4())

    usuario_id = session["usuario_id"]

   
    if menu == "parimpar" and request.method == "POST":

        numero = int(request.form.get("numero"))
        resultado = "par" if numero % 2 == 0 else "impar"

        session["numero_par"] = numero
        session["resultado_par"] = resultado

        guardar(
            "INSERT INTO par_impar (usuario_id, numero, resultado) "
            "VALUES (%s, %s, %s)",
            (usuario_id, numero, resultado)
        )

    # MULTIPLICADOR
    if menu == "multiplicador" and request.method == "POST":

        numero = int(request.form.get("numero"))

        tabla = []
        filas = []

        for i in range(1, 11):
            resultado = numero * i
            tabla.append(resultado)
            filas.append((usuario_id, numero, i, resultado))

        session["numero_multiplicador"] = numero
        session["tabla"] = tabla

        guardar(
            "INSERT INTO tabla_multiplicar "
            "(usuario_id, numero, multiplicador, resultado) "
            "VALUES (%s, %s, %s, %s)",
            filas,
            varios=True
        )

    # ADIVINA EL NÚMERO
    if menu == "adivinar" and request.method == "POST":

        accion = request.form.get("accion")

        # --- Paso 1: el usuario escribe su nombre y empieza la partida
        if accion == "iniciar":

            nombre = request.form.get("nombre", "").strip()[:50]

            if nombre:
                filas = consultar(
                    "INSERT INTO partidas (nombre, numero_secreto) "
                    "VALUES (%s, %s) RETURNING id",
                    (nombre, random.randint(1, 100))
                )
                session["partida_id"] = filas[0]["id"]
                session["nombre_jugador"] = nombre
                session["intentos"] = 0
                session["resultado_adivinar"] = None
            else:
                session["resultado_adivinar"] = "Escribe tu nombre para empezar."

        # --- Paso 2: el usuario ingresa números
        elif accion == "adivinar" and "partida_id" in session:

            numero = int(request.form.get("numero"))

            if numero < 1 or numero > 100:
                session["resultado_adivinar"] = (
                    "Debes ingresar un número entre 1 y 100."
                )
            else:
                partida_id = session["partida_id"]

                numero_secreto = consultar(
                    "SELECT numero_secreto FROM partidas WHERE id = %s",
                    (partida_id,)
                )[0]["numero_secreto"]

                session["intentos"] += 1
                intento_actual = session["intentos"]

                if numero == numero_secreto:
                    estado = "correcto"
                    mensaje = (
                        f"¡Correcto, {session['nombre_jugador']}! "
                        f"Adivinaste el número en {intento_actual} intentos."
                    )
                elif numero < numero_secreto:
                    estado = "mayor"
                    mensaje = "El número secreto es mayor. ¡Intenta nuevamente!"
                else:
                    estado = "menor"
                    mensaje = "El número secreto es menor. ¡Intenta nuevamente!"

                guardar(
                    "INSERT INTO intentos_adivinar "
                    "(partida_id, numero_ingresado, numero_intento, resultado) "
                    "VALUES (%s, %s, %s, %s)",
                    (partida_id, numero, intento_actual, estado)
                )

                if estado == "correcto":
                    # Cerrar la partida y guardar el total de intentos
                    guardar(
                        "UPDATE partidas SET total_intentos = %s, "
                        "terminada = TRUE WHERE id = %s",
                        (intento_actual, partida_id)
                    )
                    session.pop("partida_id")
                    session.pop("intentos")

                session["resultado_adivinar"] = mensaje

        # --- Abandonar: volver a pedir el nombre
        elif accion == "abandonar":

            partida_id = session.pop("partida_id", None)
            session.pop("intentos", None)
            session["resultado_adivinar"] = None

            if partida_id:
                # Borra la partida sin terminar (sus intentos se borran solos)
                guardar(
                    "DELETE FROM partidas "
                    "WHERE id = %s AND terminada = FALSE",
                    (partida_id,)
                )

    # DATOS DESDE LA BASE DE DATOS
    lista_par = []
    historial = []
    top = []

    if menu == "parimpar":
        lista_par = consultar(
            "SELECT numero, resultado, fecha FROM par_impar "
            "WHERE usuario_id = %s ORDER BY fecha DESC",
            (usuario_id,)
        )

    if menu == "adivinar":

        # Historial: nombre, fecha y números ingresados de cada partida
        historial = consultar(
            """
            SELECT p.nombre, p.fecha, p.total_intentos,
                   STRING_AGG(i.numero_ingresado::text, ', '
                              ORDER BY i.numero_intento) AS numeros
            FROM partidas p
            JOIN intentos_adivinar i ON i.partida_id = p.id
            WHERE p.terminada = TRUE
            GROUP BY p.id
            ORDER BY p.fecha DESC
            LIMIT 10
            """
        )

        # Top: mejor marca de cada persona (menos intentos = mejor puesto)
        top = consultar(
            """
            SELECT nombre, total_intentos, fecha
            FROM (
                SELECT DISTINCT ON (LOWER(nombre))
                       nombre, total_intentos, fecha
                FROM partidas
                WHERE terminada = TRUE
                ORDER BY LOWER(nombre), total_intentos ASC, fecha ASC
            ) AS mejores
            ORDER BY total_intentos ASC, fecha ASC
            LIMIT 10
            """
        )

    # MOSTRAR LA PÁGINA
    return render_template(
        "ejercicio1.html",
        menu=menu,

        numero_par=session.get("numero_par"),
        resultado_par=session.get("resultado_par"),
        lista_par=lista_par,

        numero_multiplicador=session.get("numero_multiplicador"),
        tabla=session.get("tabla", []),

        partida_activa="partida_id" in session,
        nombre_jugador=session.get("nombre_jugador"),
        resultado_adivinar=session.get("resultado_adivinar"),
        historial=historial,
        top=top
    )


if __name__ == "__main__":
    app.run(debug=True)