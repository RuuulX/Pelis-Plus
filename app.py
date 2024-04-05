from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory, jsonify, request
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
from flask import Response, url_for

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super_secret_key')
app.config['UPLOAD_FOLDER'] = 'uploads'

# Configuración de la conexión MySQL para Usuarios
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'b16_36144600_Usuarios'

# Inicializar MySQL para Usuarios
mysql_usuarios = MySQL(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/iniciar_sesion_html')
def iniciar_sesion_html():
    return render_template('iniciar_sesion_html.html')

@app.route('/registrar_html')
def registrar_html():
    return render_template('registrar_html.html')

@app.route('/login', methods=['POST'])
def login():
    usuario = request.form['usuario']
    contrasena = request.form['contrasena']

    try:
        with mysql_usuarios.connection.cursor() as cursor:
            sql_admin = "SELECT * FROM administradores WHERE usuario=%s AND contrasena=%s"
            cursor.execute(sql_admin, (usuario, contrasena))
            admin_result = cursor.fetchone()

            sql_usuario = "SELECT * FROM registrar_usuarios WHERE usuario=%s AND contrasena=%s"
            cursor.execute(sql_usuario, (usuario, contrasena))
            usuario_result = cursor.fetchone()

            if admin_result:
                session['usuario'] = usuario
                session['tipo_usuario'] = 'admin'
                return redirect(url_for('admin'))
            elif usuario_result:
                session['usuario'] = usuario
                session['tipo_usuario'] = 'user'
                return redirect(url_for('menu_principal_html'))
            else:
                return redirect(url_for('iniciar_sesion_html'))
    except Exception as e:
        print("Error:", e)
        return redirect(url_for('iniciar_sesion_html'))

@app.route('/admin')
def admin():
    if 'usuario' not in session or session['tipo_usuario'] != 'admin':
        return redirect(url_for('administrador_html'))
    return render_template('administrador_html.html')

@app.route('/user')
def user():
    return redirect(url_for('mostrar_peliculas_series'))

@app.route('/administrador_html')
def administrador_html():
    return render_template('administrador_html.html')

@app.route('/perfil_usuario')
def perfil_usuario():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion_html'))

    usuario_id = session['usuario']

    try:
        with mysql_usuarios.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM registrar_usuarios WHERE usuario = %s", (usuario_id,))
            usuario = cursor.fetchone()

        if usuario:
            return render_template('perfil_usuario_html.html', usuario=usuario)
        else:
            return "No se encontraron datos del usuario."
    except Exception as e:
        return "Error al ejecutar la consulta: " + str(e)

@app.route('/registrar', methods=['POST'])
def registrar():
    if request.method == 'POST':
        try:
            usuario = request.form['usuario']
            correo_electronico = request.form['correo_electronico']
            contrasena = request.form['contrasena']

            with mysql_usuarios.connection.cursor() as cursor:
                # Preparar y ejecutar la consulta SQL para insertar los datos en la tabla de usuarios
                sql = "INSERT INTO registrar_usuarios (usuario, correo_electronico, contrasena) VALUES (%s, %s, %s)"
                cursor.execute(sql, (usuario, correo_electronico, contrasena))
                mysql_usuarios.connection.commit()
                return redirect('/iniciar_sesion_html')
        except Exception as err:
            print("Error al registrar usuario:", err)
            return redirect('/registrar_html')

@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    return redirect(url_for('iniciar_sesion_html'))

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        tipo = request.form['tipo']
        link = request.form['link']
        nombre = request.form['nombre']
        sinopsis = request.form['sinopsis']
        genero = request.form['genero']

        if 'imagen' not in request.files:
            return "No se ha seleccionado ninguna imagen."

        imagen = request.files['imagen']

        if imagen.filename == '':
            return "No se ha seleccionado ninguna imagen."

        if tipo not in ["pelicula", "serie"]:
            return "Tipo de contenido no válido."

        target_dir = os.path.join(app.config['UPLOAD_FOLDER'], tipo)

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join(target_dir, filename))

        # Guardar la ruta relativa de la imagen en la base de datos
        imagen_path = os.path.join(tipo, filename)

        with mysql_usuarios.connect.cursor() as cursor:
            cursor.execute("INSERT INTO peliculas_series (tipo, imagen, link, nombre, sinopsis, genero) VALUES (%s, %s, %s, %s, %s, %s)",
                           (tipo, imagen_path, link, nombre, sinopsis, genero))
        mysql_usuarios.connect.commit()

        return render_template('administrador_html.html', message="Película o serie subida exitosamente.", error=None   ), 200
    except Exception as e:
        print("Error en la carga de archivos:", e)
        return render_template('administrador_html.html', message=None, error="Error interno del servidor al cargar el archivo. Por favor, inténtelo de nuevo más tarde.")

@app.route('/menu_principal_html')
def menu_principal_html():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion_html'))

    usuario = session['usuario']

    try:
        peliculas_series = obtener_peliculas_series()

        if peliculas_series:
            return render_template('menu_principal_html.html', usuario=usuario, peliculas_series=peliculas_series)
        else:
            return render_template('menu_principal_html.html', mensaje="No hay películas o series disponibles.")
    except Exception as e:
        print("Error al obtener información:", e)
        return render_template('menu_principal_html.html', mensaje="Error al obtener información. Por favor, inténtelo de nuevo más tarde.")

# Función para obtener los datos de películas y series
def obtener_peliculas_series():
    try:
        with mysql_usuarios.connect.cursor() as cursor:
            cursor.execute("SELECT nombre, genero, tipo, imagen FROM peliculas_series")
            peliculas_series = cursor.fetchall()
            return peliculas_series
    except Exception as e:
        print("Error al obtener películas y series:", e)
        return None

@app.route('/uploads/<path:filename>')
def send_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/reproducir/<nombre>')
def reproducir(nombre):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion_html'))

    usuario = session['usuario']

    try:
        with mysql_usuarios.connection.cursor() as cursor:
            sql = "SELECT link, sinopsis FROM peliculas_series WHERE nombre = %s"
            cursor.execute(sql, (nombre,))
            result = cursor.fetchone()
            if result:
                link = result[0]  # Acceder al primer elemento de la tupla
                sinopsis = result[1]  # Acceder al segundo elemento de la tupla
                return render_template('reproducir_html.html', nombre=nombre, link=link, sinopsis=sinopsis, usuario=usuario)
            else:
                return "No se encontró la película o serie en la base de datos."
    except Exception as e:
        return "Error: " + str(e)

@app.route('/procesar_comentario', methods=['POST'])
def procesar_comentario():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion_html'))
    
    usuario = session['usuario']
    comentario = request.form['comentario']
    nombre_pelicula_serie = request.form['nombre_pelicula_serie']

    try:
        with mysql_usuarios.connect.cursor() as cursor:
            sql = "INSERT INTO comentarios (usuario, comentario, nombre_pelicula_serie) VALUES (%s, %s, %s)"
            cursor.execute(sql, (usuario, comentario, nombre_pelicula_serie))
            mysql_usuarios.connect.commit()
            return redirect(url_for('reproducir', nombre=nombre_pelicula_serie))
    except Exception as e:
        return "Error: " + str(e)
@app.route('/mostrar_peliculas_series')
def mostrar_peliculas_series():
    try:
        with mysql_usuarios.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM peliculas_series")
            peliculas_series = cursor.fetchall()
            return render_template('menu_principal_html.html', peliculas_series=peliculas_series)
    except Exception as e:
        print("Error al obtener películas y series:", e)
        return "Error interno del servidor al obtener películas y series de la base de datos.", 500


@app.route('/buscar')
def buscar():
    search = request.args.get('search')
    # Obtener las películas y series
    peliculas_series = obtener_peliculas_series()
    if peliculas_series is None:
        return "Error al obtener películas y series."

    # Filtrar las películas y series por el término de búsqueda
    peliculas_filtradas = []
    for pelicula_serie in peliculas_series:
        if search.lower() in pelicula_serie[0].lower():
            peliculas_filtradas.append(pelicula_serie)

    # Crear el HTML para mostrar las películas y series filtradas
    html = ''
    for pelicula in peliculas_filtradas:
        html += f'<a href="{url_for("reproducir", nombre=pelicula[0])}" class="movie {pelicula[2]}">'
        html += f'<img src="{url_for("send_image2", filename=f"pelicula/{pelicula[3].split("/")[-1]}")}" alt="{pelicula[0]}">'
        html += f'<p>Género: {pelicula[1]}</p>'
        html += f'<p>{pelicula[0]}</p></a>'

    # Enviar el HTML al cliente
    return Response(html, content_type='text/html')


@app.route('/uploads/<path:filename>')
def send_image2(filename):
   return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/ver_contenido', methods=['GET', 'POST'])
def ver_contenido():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion_html'))

    if request.method == 'POST':
        usuario = session['usuario']
        comentario = request.form['comentario']
        nombre_pelicula_serie = request.form['nombre_pelicula_serie']

        try:
            with mysql_usuarios.connection.cursor() as cursor:
                sql = "INSERT INTO comentarios (usuario, comentario, nombre_pelicula_serie) VALUES (%s, %s, %s)"
                cursor.execute(sql, (usuario, comentario, nombre_pelicula_serie))
                mysql_usuarios.connection.commit()
                return redirect(url_for('reproducir', nombre=nombre_pelicula_serie))
        except Exception as e:
            return "Error al procesar el comentario: " + str(e)

    return render_template('reproducir_html.html')

if __name__ == '__main__':
    app.run(debug=True)
