import socket
import time

ROBOT_IP = "192.168.56.102"
PORT = 30002

script = """
def test_pose_pieza1():
  textmsg("TEST PIEZA 1 - POSE EXACTA MEDIDA")

  set_tcp(p[0,0,0,0,0,0])

  # Pose exacta medida en el centro bueno
  movej(p[0.16854, -0.39694, 0.12000, 2.79604, -1.43234, 0.00003], a=0.03, v=0.05)
  sleep(1.0)

  movel(p[0.16854, -0.39694, 0.01120, 2.79604, -1.43234, 0.00003], a=0.02, v=0.01)
  sleep(2.0)

  movel(p[0.16854, -0.39694, 0.12000, 2.79604, -1.43234, 0.00003], a=0.02, v=0.02)
end

test_pose_pieza1()
"""

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((ROBOT_IP, PORT))
    s.sendall((script + "\n").encode("utf-8"))
    time.sleep(2)