import socket

HOST = "192.168.56.2"
PORT = 50001

print(f"PC escuchando en {HOST}:{PORT}...")

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind((HOST, PORT))
srv.listen(1)

conn, addr = srv.accept()
print("Conectado desde:", addr)

data = conn.recv(1024)
print("Recibido:", data.decode("utf-8", errors="ignore"))

conn.close()
srv.close()
print("Servidor cerrado.")