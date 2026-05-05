# -*- coding: utf-8 -*-
"""
main.py
=======
Punto de entrada del sistema de dibujo colaborativo UR3e + UR5e.

Flujo completo:
  1. Carga y procesa la imagen → mapa de bordes
  2. Extrae trayectorias métricas centradas en el origen (centro del papel)
  3. Reparte trayectorias entre UR3e y UR5e (aleatorio + filtro de alcance)
  4. Genera los dos URScripts
  5. Envía UR3e primero; cuando acaba y avisa al PC, se envía UR5e

Uso:
    python main.py imagen.jpg
    python main.py imagen.jpg --seed 42         # reparto reproducible
    python main.py imagen.jpg --dry-run         # solo genera scripts, no envía
    python main.py imagen.jpg --base-origen ur3e # usa UR3e como referencia principal
    python main.py imagen.jpg --ip3 192.168.1.10 --ip5 192.168.1.11
"""

import sys
import logging      # Para mostrar información y errores de forma clara por consola.
import argparse     # Sirve para leer argumentos en la terminal

# Importar funciones de los módulos del proyecto
from config_solucion             import UR3E_IP, UR5E_IP, PORT, Z_PAPEL, F_DETECT
from image_processing     import cargar_imagen, preprocesar_imagen, guardar_debug
from trajectory           import extraer_trayectorias
from distributor          import repartir_trayectorias, resumen_reparto
from urscript_generator_solucion   import generar_script_ur3e, generar_script_ur5e, guardar_script
from robot_comm_solucion           import enviar_scripts_dual

# =============================================================================
# LOGGING
# =============================================================================
# Configura cómo se muestran los msg en la terminal
logging.basicConfig(
    level=logging.INFO, # Muestra mensajes informativos y de error (SOLO)
    format="%(asctime)s [%(levelname)s] %(message)s", # Formato: hora + tipo de mensaje + texto
    datefmt="%H:%M:%S", # Formato de la hora: horas:minutos:segundos
)
log = logging.getLogger(__name__) # Crea un "logger" propio usado para mostrar mensajes

DEFAULT_IMAGE = r"C:\Users\Sofia\Desktop\codigosPythonUR\imagenes\flor_simple.jpg"


def parse_args():
    """
    Esta función lee los argumentos de la terminal.

    Por ejemplo:
        python main.py flor.jpg --dry-run --base-origen ur3e

    Devuelve un objeto llamado args con todos esos valores.
    """
    # TODOS LOS ARGUMENTOS SON OPCIONALES, PORQUE TIENEN VALORES POR DEFECTO (DEFAULT).
        # Se pueden especificar todos, algunos o ninguno. 
        # Si no se especifica alguno, se usa el valor por defecto.
    p = argparse.ArgumentParser(  
        description="Dibujo colaborativo UR3e + UR5e." )               # Es el objeto que entiende los argumentos dados en la terminal.                                         
    p.add_argument("imagen", nargs="?", default=None,
                   help=f"Imagen JPG/PNG. Default: {DEFAULT_IMAGE}")   # Argumento que indica la imagen. Si no se da, se usa DEFAULT_IMAGE.
    p.add_argument("--ip3",  default=UR3E_IP,
                   help=f"IP del UR3e. Default: {UR3E_IP}")
    p.add_argument("--ip5",  default=UR5E_IP,
                   help=f"IP del UR5e. Default: {UR5E_IP}")
    p.add_argument("--port", default=PORT, type=int,
                   help=f"Puerto URScript. Default: {PORT}")
    
    p.add_argument("--seed", default=None, type=int,
                   help="Semilla aleatoria para el reparto (reproducibilidad).")
    p.add_argument("--dry-run", action="store_true",
                   help="Genera los scripts pero NO los envía a los robots.")
    
    # Nombres del archivos donde se guardarán los scripts de UR3e y UR5e
    p.add_argument("--out3",  default="script_ur3e.urscript",
                   help="Archivo de salida script UR3e.")
    p.add_argument("--out5",  default="script_ur5e.urscript",
                   help="Archivo de salida script UR5e.")
    
    p.add_argument("--debug-edges", default="debug_edges.png",
                   help="Imagen de bordes para depuración.")
    
    # choices=["ur3e", "ur5e"] significa que solo acepta esos dos valores.
    # Por defecto se usa ur3e, porque tiene menos alcance y conviene ajustar
    # el dibujo a su zona útil.
    p.add_argument("--base-origen", default="ur3e", choices=["ur3e", "ur5e"],
                   help="Robot que se usa como referencia principal del origen común. Default: ur3e.")
    return p.parse_args()


def main():
    # Lee los argumentos de la terminal.
    args = parse_args()
    
    # Decide qué imagen se usará.
    image_path = args.imagen or DEFAULT_IMAGE

    # Muestra cabecera informativa en la terminal.
    log.info("=" * 60)
    log.info("  Sistema de dibujo colaborativo  UR3e + UR5e")
    log.info("=" * 60)
    
    # Muestra la ruta de la imagen
    log.info(f"  Imagen     : {image_path}")
    
    # Muestra las IP's y los puertos de los robots
    log.info(f"  UR3e       : {args.ip3}:{args.port}")
    log.info(f"  UR5e       : {args.ip5}:{args.port}")
    
    # Muestra altura extra sobre papel / fuerza de detección de mesa / semilla / base origen
    log.info(f"  Z_PAPEL    : {Z_PAPEL * 1000:.1f} mm sobre contacto")
    log.info(f"  F_DETECT   : {F_DETECT:.1f} N (umbral detección mesa)")
    log.info(f"  Semilla    : {args.seed}")
    log.info(f"  Dry-run    : {args.dry_run}") 
    log.info(f"  Base origen: {args.base_origen}")
    
    log.info("  Sensor F/T : Habilitado (detección automática de mesa una sola vez)")
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Procesar imagen
    # ------------------------------------------------------------------
    try:
        # Carga la imagen desde la ruta image_path.
        # Devuelve una imagen en formato OpenCV.
        img   = cargar_imagen(image_path)
        
        # Procesa la imagen para extraer bordes.
        # Aquí se aplican filtros, escala de grises, Canny
        edges = preprocesar_imagen(img)
        
        # Guarda una imagen de depuración con los bordes detectados.
        # Así puedes abrir debug_edges.png y comprobar si la imagen se detectó bien.
        guardar_debug(edges, args.debug_edges)
        
    except (FileNotFoundError, ValueError) as e:
        log.error(f"Error de imagen: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Extraer trayectorias
    # ------------------------------------------------------------------
    try:
        # Convierte los bordes detectados en trayectorias métricas.
        #
        # edges contiene los bordes de la imagen.
        # img.shape contiene tamaño de imagen: alto, ancho y canales.
        #
        # El resultado, trayectorias, es una lista de trazos.
        # Cada trazo es una lista de puntos (x, y) en metros.
        trayectorias = extraer_trayectorias(edges, img.shape)
     
    # Si no hay contornos válidos, se captura el error.   
    except ValueError as e:
        log.error(f"Error de trayectorias: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Repartir entre robots
    # ------------------------------------------------------------------
    
        # Divide las trayectorias entre UR3e y UR5e.
        #
        # t_ur3e contiene los trazos que hará el UR3e.
        # t_ur5e contiene los trazos que hará el UR5e.
        #
        # La función tiene en cuenta el alcance del UR3e.
        # Si una trayectoria queda fuera del alcance seguro del UR3e,
        # se manda al UR5e.
    
    t_ur3e, t_ur5e = repartir_trayectorias(trayectorias, semilla=args.seed)
    log.info(resumen_reparto(t_ur3e, t_ur5e))

    # COMPROBACIONES tienen trayectorias 
    if not t_ur3e:
        log.error("Al UR3e no le han asignado trayectorias. "
                  "Revisa MAX_ANCHO_M o la posición del papel.")
        sys.exit(1)
    if not t_ur5e:
        log.error("Al UR5e no le han asignado trayectorias.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Generar URScripts
    # ------------------------------------------------------------------
    
        # Genera el programa URScript para el UR3e.
        #
        # Se le pasan:
        # - las trayectorias que debe dibujar el UR3e
        # - la base de origen seleccionada: ur3e o ur5e
        
    try:
        script_ur3e = generar_script_ur3e(t_ur3e, base_origen=args.base_origen)
        script_ur5e = generar_script_ur5e(t_ur5e, base_origen=args.base_origen)
        
    except ValueError as e:
        log.error(f"Error al generar scripts: {e}")
        sys.exit(1)

    guardar_script(script_ur3e, args.out3)
    guardar_script(script_ur5e, args.out5)
    
    log.info(f"Scripts guardados: {args.out3}  |  {args.out5}")

    # ------------------------------------------------------------------
    # 5. Enviar a los robots
    # ------------------------------------------------------------------
    
        # Si se ha activado --dry-run, no se envía nada a los robots.
        # Solo se generan y guardan los scripts.
    if args.dry_run:
        log.info("Dry-run activado — scripts generados pero NO enviados.")
        log.info(f"Revisa los scripts en: {args.out3} y {args.out5}")
        return

    try:
         # Envía los scripts a los robots.
        #
        # Esta función está en robot_comm_solucion.py.
        #
        # Según tu lógica actual:
        # 1. Se envía primero el script al UR3e.
        # 2. El UR3e dibuja.
        # 3. Cuando termina, manda LISTO al PC.
        # 4. Entonces el PC envía el script al UR5e.
        #
        # Esto evita que ambos robots se muevan a la vez si no quieres
        # arriesgar colisiones.
        
        enviar_scripts_dual(
            script_ur3e, script_ur5e,
            ip_ur3e=args.ip3,
            ip_ur5e=args.ip5,
            port=args.port,
        )
    except ConnectionError as e:
        log.error(str(e))
        sys.exit(1)

    log.info("Sistema dual en marcha. Sigue el progreso en las tablets.")


if __name__ == "__main__":
    main()
