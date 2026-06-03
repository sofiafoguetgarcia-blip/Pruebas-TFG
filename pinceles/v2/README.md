# Proyecto UR5e + UR3e: manipulación y pintura de baldosas

Este proyecto parte de la versión anterior en la que el UR5e manipulaba baldosas y el UR3e dibujaba sobre ellas. En esta nueva versión se mantiene la lógica del UR5e y se cambia la tarea del UR3e.

## Funcionamiento general

1. El PC lee el archivo JSON generado por visión artificial.
2. El UR5e recibe la posición de la baldosa en coordenadas del UR5e.
3. El UR5e recoge la baldosa mediante ventosa.
4. El UR5e deja la baldosa en la zona compartida.
5. El UR5e vuelve a HOME y se queda reposando.
6. El PC recibe el aviso del UR5e y envía el script al UR3e.
7. El UR3e va al cuenco de pintura.
8. El UR3e moja el pincel y limpia el exceso en los laterales del cuenco.
9. El UR3e va a la zona compartida.
10. El UR3e detecta la superficie de la baldosa por fuerza.
11. El UR3e pinta la baldosa completa mediante pasadas paralelas suaves.
12. El UR3e vuelve a HOME y avisa al PC.
13. El PC espera 5 segundos.
14. El UR5e recoge la baldosa pintada y la devuelve a su posición original.

## Archivos principales

- `main.py`: punto de entrada del proyecto.
- `config.py`: parámetros generales, poses, velocidades, ventosa y configuración de pintura.
- `vision.py`: lectura del JSON de visión artificial.
- `transform.py`: mantiene la conversión entre zonas compartidas de UR5e y UR3e.
- `urscript_generator.py`: genera los scripts URScript de recogida, pintura y devolución.
- `robot_comm.py`: coordina la comunicación PC-robots mediante sockets.

## Uso rápido

```bash
python main.py --dry-run
```

Genera los scripts sin enviarlos a los robots.

```bash
python main.py --pieza 3 --dry-run
```

Genera únicamente los scripts de la pieza 3.

```bash
python main.py
```

Ejecuta el flujo completo para todas las piezas del JSON.

## Salida

Los scripts se guardan en la carpeta:

```text
Resultados/
```

Con este formato:

```text
pieza_1_ur5_recoger.urscript
pieza_1_ur3_pintar.urscript
pieza_1_ur5_devolver.urscript
```

## Ajustes importantes

La pose del cuenco está en `config.py`:

```python
UR3E_PAINT_BOWL_POSE = [-0.32525, -0.09942, 0.12597, 0.93000, 3.00100, 0.00000]
```

La posición original estaba expresada en milímetros para X/Y/Z y se ha convertido a metros para URScript.

Los parámetros de pintura también están en `config.py`:

```python
PAINT_MARGIN_M
PAINT_PASS_SPACING_M
PAINT_SAFE_Z_OFFSET
PAINT_CONTACT_OFFSET_M
V_PINTURA
A_PINTURA
```

La espera de 5 segundos antes de que el UR5e recoja la baldosa pintada está en:

```python
ESPERA_SECADO_ANTES_DEVOLVER = 5.0
```
