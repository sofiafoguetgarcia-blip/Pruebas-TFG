# -*- coding: utf-8 -*-
"""
robot_comm.py
=============
Este archivo se encarga de la comunicación entre el PC y los robots.

No genera trayectorias.
No procesa imágenes.
No calcula poses.

Su trabajo es:
1. Enviar el script al UR3e.
2. Esperar a que el UR3e termine.
3. Recibir el mensaje LISTO.
4. Enviar después el script al UR5e.

Así se evita que los dos robots se muevan a la vez.
"""

import socket
import time
import logging

from config_solucion import UR3E_IP, UR5E_IP, PORT, PORT_UR3_DONE, SYNC_MSG

log = logging.getLogger(__name__)


def _enviar(ip: str, port: int, script: str, timeout: float = 5.0, pausa: float = 2.0) -> None:
    """
    Envía un URScript a un robot por TCP.
        Esta función abre una conexión con el robot,
            manda el texto del programa URScript,
            espera un poco y cierra la conexión.
    """
    
    log.info(f"Conectando a {ip}:{port}...")
    
    # Crea un socket TCP.
    #
        # AF_INET significa IPv4.
        # SOCK_STREAM significa TCP.
        #
    # El uso de "with" hace que el socket se cierre automáticamente
    # al salir del bloque.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        
        s.settimeout(timeout)                                               # Define un tiempo máximo de espera.
                                                                            # Si el robot no responde en ese tiempo, dará error.
        
        s.connect((ip, port))                                               # Conecta el PC con el robot usando IP y puerto.
        
        # Envía el script al robot.
        s.sendall((script + "\n").encode("utf-8"))                          # script + "\n" añade un salto de línea final.
                                                                                # encode("utf-8") convierte el texto en bytes,
                                                                                # que es lo que se puede mandar por socket.
                                                            
        log.info(f"Script enviado a {ip} ({len(script)} caracteres)")       # Informa de que el script se ha enviado.
        time.sleep(pausa)
        
    log.info(f"Conexión cerrada: {ip}")                                     # Al salir del with, el socket ya está cerrado.


def _crear_servidor_ur3_done(timeout: float = 1200.0):
    """ 
    Crea un servidor TCP en el PC para recibir LISTO del UR3e.

    """
    
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 # Crea un socket TCP para el servidor del PC.
    
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)               # Permite reutilizar el puerto aunque se haya usado antes.
                                                                                #
                                                                                # Esto evita errores típicos como:
                                                                                # "Address already in use"
                                                                                # después de cerrar y volver a ejecutar rápido.
                                                                                
    srv.bind(("0.0.0.0", PORT_UR3_DONE))                                     # Asocia el servidor a todas las interfaces de red del PC.
                                                                                #
                                                                                # "0.0.0.0" significa:
                                                                                # escucha en cualquier IP del PC.
                                                                                #
                                                                                # PORT_UR3_DONE es el puerto configurado para recibir LISTO.

    srv.listen(1)                                                            # Pone el socket en modo escucha.
                                                                                # listen(1) significa que acepta una conexión pendiente.
    
    srv.settimeout(timeout)                                                  # Define un tiempo máximo de espera para recibir la conexión.                                                 
    
    log.info(f"PC escuchando LISTO del UR3e en puerto {PORT_UR3_DONE}...")
    return srv

def esperar_listo_ur3e():
    """
    Abre un servidor TCP en el PC y espera a que el UR3e mande LISTO.

    Esta función se ejecuta en un hilo separado.
    Así el PC puede quedarse esperando mientras también envía el script al UR3e.
    """
    

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 50001))
    srv.listen(1)                                                            # Servidor en modo escucha, esperando una conexión del UR3e.

    log.info("PC esperando LISTO del UR3e en puerto 50001...")

    conn, addr = srv.accept()                                               # Espera hasta que alguien se conecte.
                                                                                # En este caso, debe conectarse el UR3e al terminar su dibujo.
                                                                                    # conn es la conexión con el robot.
                                                                                    # addr es la dirección desde donde se ha conectado
    log.info(f"Conexión recibida desde: {addr}")

    data = conn.recv(1024).decode("utf-8", errors="ignore")                 # Recibe hasta 1024 bytes del UR3e.
                                                                                # decode convierte los bytes recibidos a texto.
                                                                                # errors="ignore" evita que el programa falle si llega algún carácter raro.
    log.info(f"Mensaje recibido del UR3e: {data}")

    conn.close()
    srv.close()

    if "LISTO" not in data:                                                 # Si no contiene LISTO, se considera error de sincronización.
        raise ConnectionError(f"Mensaje inesperado del UR3e: {data}")


def enviar_scripts_dual(script_ur3e, script_ur5e, ip_ur3e, ip_ur5e, port):
    """
    Envía los scripts en orden seguro.

    Orden:
    1. El PC abre servidor esperando LISTO.
    2. El PC envía script al UR3e.
    3. El UR3e dibuja.
    4. El UR3e manda LISTO al PC.
    5. El PC recibe LISTO.
    6. El PC envía script al UR5e.
    """
    
    log.info("Abriendo servidor PC para esperar al UR3e...")

    # Abrir servidor ANTES de enviar al UR3e
    import threading                                                       # threading permite ejecutar una función en paralelo.

    error_sync = []                                                        # Lista para guardar errores que ocurran dentro del hilo servidor.
                                                                                # Se usa una lista porque desde dentro de la función servidor()
                                                                                # se puede modificar con append().             

    def servidor():
        """
        Función interna que espera el mensaje LISTO.

        Se ejecutará en un hilo separado.
        """
        
        try:                                                               # Espera a que el UR3e conecte al PC y mande LISTO.
            esperar_listo_ur3e()
        except Exception as e:                                             # Si ocurre cualquier error, se guarda en error_sync.
            error_sync.append(e)                                                                
                                                                            # No se puede hacer raise directamente desde el hilo
                                                                            # y capturarlo fuera fácilmente, por eso se guarda aquí.
            

    hilo = threading.Thread(target=servidor)                               # Crea un hilo que ejecutará la función servidor().
    hilo.start()

    time.sleep(1.0)

    log.info("Enviando script al UR3e...")
    _enviar(ip_ur3e, port, script_ur3e)

    log.info("Esperando a que UR3e termine y avise al PC...")
    hilo.join()                                                            # Espera a que el hilo termine, es decir, a que se reciba LISTO o ocurra un error.  

    if error_sync:                                                         
        raise ConnectionError(error_sync[0])

    log.info("UR3e ha terminado. Enviando script al UR5e...")
    _enviar(ip_ur5e, port, script_ur5e)

    log.info("Script enviado al UR5e.")