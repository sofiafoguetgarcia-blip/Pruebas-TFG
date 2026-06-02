# -*- coding: utf-8 -*-

import socket
import time

UR5E_IP = "192.168.56.102"
PORT = 30002

SCRIPT = """
def prueba_ventosa_contacto_ur5e():

  textmsg("=== INICIO PRUEBA VENTOSA UR5e ===")

  # Guardar la posicion inicial exacta del robot
  pose_inicio = get_actual_tcp_pose()

  # Parametros
  fuerza_umbral = 1.2
  velocidad_bajada = 0.003

  # Aumentamos mucho el limite para que pueda bajar desde mas altura
  max_iteraciones = 30000

  textmsg("UR5e: posicion inicial guardada")

  zero_ftsensor()
  sleep(0.5)

  textmsg("UR5e: bajando hasta detectar contacto")

  i = 0
  while (force() < fuerza_umbral and i < max_iteraciones):
    speedl([0, 0, -velocidad_bajada, 0, 0, 0], 0.05, 0.008)
    i = i + 1
  end

  # Parada inmediata al detectar contacto
  stopl(0.2)
  sleep(0.1)

  if (i >= max_iteraciones):
    popup("UR5e: no se detecto contacto. Revisa altura inicial.", error=True)
    halt
  end

  textmsg("UR5e: contacto detectado")

  # Guardar la posicion exacta donde se detecta la pieza
  pose_contacto = get_actual_tcp_pose()

  # Activar ventosa inmediatamente, sin bajar mas ni presionar
  textmsg("UR5e: activando ventosa")
  set_digital_out(0, True)
  sleep(0.7)

  # Subir directamente a la posicion inicial guardada
  textmsg("UR5e: subiendo a posicion inicial con la baldosa")
  movel(pose_inicio, a=0.03, v=0.02)

  # Esperar 5 segundos
  textmsg("UR5e: esperando 5 segundos")
  sleep(5.0)

  # Bajar a la misma posicion donde cogio la baldosa
  textmsg("UR5e: bajando para dejar la baldosa")
  movel(pose_contacto, a=0.03, v=0.02)

  # Soltar ventosa
  textmsg("UR5e: soltando ventosa")
  set_digital_out(0, False)
  sleep(0.5)

  # Volver a la posicion inicial
  textmsg("UR5e: volviendo a posicion inicial")
  movel(pose_inicio, a=0.03, v=0.02)

  textmsg("=== FIN PRUEBA VENTOSA UR5e ===")

end

prueba_ventosa_contacto_ur5e()
"""

def enviar_script_ur5e():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((UR5E_IP, PORT))
        s.sendall(SCRIPT.encode("utf-8"))
        time.sleep(1)

if __name__ == "__main__":
    enviar_script_ur5e()