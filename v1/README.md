# Sistema de dibujo colaborativo  UR3e + UR5e

## Estructura del proyecto

```
ur_dual_drawing/
├── config.py               ← IPs, alcances, velocidades, parámetros de Z
├── image_processing.py     ← Carga imagen + detección de bordes
├── trajectory.py           ← Bordes → trayectorias métricas (dx, dy)
├── distributor.py          ← Reparto aleatorio + filtro de alcance
├── urscript_generator.py   ← Genera script UR3e y script UR5e
├── robot_comm.py           ← Envío TCP a ambos robots
└── main.py                 ← Orquestador + CLI
```

## Flujo completo

```
PC central
    │
    ├─ imagen → bordes → trayectorias → reparto (50/50 aleatorio)
    │
    ├─ genera script_ur5e.urscript  ──► envía al UR5e  (primero)
    │                                       │
    │                                       └─ levanta socket servidor
    │                                          en PORT_SYNC, espera...
    │
    └─ genera script_ur3e.urscript  ──► envía al UR3e  (2s después)
                                            │
                                            ├─ guarda HOME (joints actuales)
                                            ├─ detecta mesa (force_mode)
                                            ├─ dibuja su mitad
                                            ├─ vuelve a HOME
                                            └─ socket → UR5e: "LISTO"
                                                            │
                                                        UR5e recibe LISTO
                                                            ├─ detecta mesa
                                                            ├─ dibuja su mitad
                                                            └─ vuelve a HOME
```

## Sincronización robot→robot

El UR3e tiene al final de su script:
```
socket_open("IP_UR5E", 50001)
socket_send_string("LISTO")
socket_close()
```

El UR5e tiene al principio:
```
socket_open("0.0.0.0", 50001, "sync_server")
while msg != "LISTO":
    esperar...   ← textmsg cada 10s visible en tablet
end
```

Ambos mensajes son visibles en el log de la tablet de cada robot.

## Uso

```bash
# Ejecución normal
python main.py mi_imagen.jpg

# Reparto reproducible (misma semilla = mismo reparto)
python main.py mi_imagen.jpg --seed 42

# Solo generar scripts, no enviar
python main.py mi_imagen.jpg --dry-run

# IPs personalizadas
python main.py mi_imagen.jpg --ip3 192.168.1.10 --ip5 192.168.1.11
```

## Configuración antes de ejecutar

Editar `config.py`:

1. `UR3E_IP` / `UR5E_IP` — IPs de los robots en tu red
2. `UR3E_TCP_ORIGEN` / `UR5E_TCP_ORIGEN` — poses TCP del centro del papel
   en el frame base de cada robot (ya configuradas según tus medidas)
3. `Z_PAPEL` — offset sobre el contacto (subir si aprieta, bajar si no pinta)
4. `MAX_ANCHO_M` — tamaño físico del dibujo en metros (0.15 para 15 cm)

## Importante: posición HOME

Coloca cada robot en su posición de reposo ANTES de ejecutar el script.
El programa lee `get_actual_joint_positions()` al arrancar y esa posición
se convierte en el HOME al que vuelve al terminar.
