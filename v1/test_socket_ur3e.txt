import socket

ROBOT_IP = "192.168.56.101"
PORT = 30002

script = """
def test_socket():
  textmsg("UR3e intentando conectar con PC")
  ok = socket_open("192.168.56.2", 50001, "pc_sync")

  if ok:
    textmsg("UR3e conectado al PC")
    socket_send_string("LISTO", "pc_sync")
    sleep(0.5)
    socket_close("pc_sync")
    textmsg("UR3e mensaje enviado")
  else:
    popup("UR3e NO pudo conectar con el PC", error=True)
    halt
  end
end

test_socket()
"""

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(5)
    s.connect((ROBOT_IP, PORT))
    s.sendall((script + "\n").encode("utf-8"))

print("Test socket enviado al UR3e")