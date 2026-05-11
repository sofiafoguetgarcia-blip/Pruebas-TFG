# Proyecto UR5e + UR3e: manipulación simulada de baldosa y dibujo adaptado mediante JSON

Esta versión está adaptada a la situación actual del proyecto:

- No se usa cámara en este programa.
- No se procesa una imagen de escena dentro de este programa.
- La visión artificial se ejecuta antes y genera un archivo JSON.
- Este programa solo lee el JSON y usa sus coordenadas para mover el UR5e.
- El UR5e simula coger y soltar la baldosa.
- El UR3e dibuja en la zona compartida y adapta el tamaño del dibujo al tamaño de la pieza indicada en el JSON.

## Flujo

1. El script de visión artificial externo genera `datos_robot.json`.
2. `main.py` lee el JSON.
3. Se selecciona una pieza mediante `--pieza`.
4. Se toman del JSON:
   - `robot_x`
   - `robot_y`
   - `ancho_mm`
   - `alto_mm`
   - `angulo_grados`
5. `vision.py` convierte las coordenadas de milímetros a metros.
6. El dibujo se escala según el lado menor de la pieza.
7. Se generan tres scripts:
   - `script_ur5e_recoger.urscript`
   - `script_ur3e_dibujar.urscript`
   - `script_ur5e_devolver.urscript`
8. Si no está activo `--dry-run`, el PC ejecuta la secuencia:
   - UR5e recoge la baldosa indicada por el JSON.
   - UR5e la lleva a la zona compartida.
   - UR3e dibuja.
   - UR5e devuelve la baldosa al punto original.

## Formato del JSON

El programa espera exactamente un JSON como este:

```json
{
  "imagen": "DSC07665.jpg",
  "pipeline": "clasico",
  "total_piezas": 9,
  "piezas": [
    {
      "numero": 1,
      "robot_x": 97.74,
      "robot_y": -327.53,
      "ancho_mm": 141.1,
      "alto_mm": 142.08,
      "angulo_grados": 7.5
    }
  ],
  "calibracion": {
    "escala_x_mm_px": -0.347375,
    "escala_y_mm_px": -0.30889,
    "offset_x_mm": 397.18,
    "offset_y_mm": -86.91
  }
}
```

## Uso recomendado primero

```bash
python main.py --json datos_robot.json --pieza 1 --dibujo flor.jpg --dry-run
```

Esto genera los scripts sin mover los robots.

## Uso con robots

```bash
python main.py --json datos_robot.json --pieza 1 --dibujo flor.jpg
```

## Archivos principales

- `main.py`: flujo completo usando únicamente el JSON de visión.
- `vision.py`: lectura del JSON y conversión de milímetros a metros.
- `datos_robot.json`: ejemplo real de salida del script de visión artificial.
- `image_processing.py`: procesamiento de la imagen del dibujo.
- `trajectory.py`: conversión de bordes a trayectorias métricas.
- `urscript_generator.py`: generación de los tres URScripts.
- `robot_comm.py`: envío de scripts y sincronización por sockets.
- `config.py`: IPs, velocidades, fuerza, zona compartida y escalado.

## Nota importante sobre unidades

El JSON usa milímetros:

```json
"robot_x": 97.74,
"robot_y": -327.53
```

URScript usa metros. Por eso `vision.py` convierte esos valores automáticamente:

```python
x_robot = robot_x / 1000.0
y_robot = robot_y / 1000.0
```

Por ejemplo:

```text
robot_x = 97.74 mm  ->  0.09774 m
robot_y = -327.53 mm -> -0.32753 m
```

## Seguridad

Antes de ejecutar en robots reales:

1. Ejecuta siempre con `--dry-run`.
2. Revisa los `.urscript` generados.
3. Comprueba que la pieza seleccionada con `--pieza` es la correcta.
4. Comprueba que las coordenadas del JSON son alcanzables para el UR5e.
5. Mantén velocidades bajas.
6. Ten la mano cerca del paro.
7. Comprueba que `DROP_ZONE_UR3E` y `DROP_ZONE_UR5E` representan el mismo punto físico.
