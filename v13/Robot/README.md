# Sistema de Detección de Piezas Cerámicas para Robot

Este proyecto detecta automáticamente piezas de pavimento cerámico desde una imagen, calcula su centro, dimensiones y ángulo de giro, y convierte las coordenadas al sistema de medidas del robot (milímetros).

## ¿Qué hace?

- **Detecta** cada pieza cerámica visible en la imagen.
- **Calcula** su centro, ancho, alto y ángulo de rotación.
- **Calibra** la imagen usando dos cruces de referencia para pasar de píxeles a milímetros.
- **Genera** imágenes anotadas y archivos JSON listos para ser usados por un cobot.

## Requisitos

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes recomendado)

## Dependencias

- `numpy >= 2.4.4`
- `opencv-python >= 4.13.0.92`

## Instalación

```bash
cd /workspaces/Container1/Robot
uv sync
```

> Si no usas `uv`, puedes instalar las dependencias manualmente con `pip install numpy opencv-python`.

## Uso

Ejecuta el orquestador principal:

```bash
python main.py
```

Verás en consola un resumen similar a este:

```
Piezas detectadas: 9

 N°        Centro          Ancho     Alto     Ángulo
-------------------------------------------------------
  1  (  862,   779)      430px      433px      7.50°
  ...
```

Los resultados se guardan automáticamente en la carpeta `resultados/`.

## Estructura del proyecto

```
Robot/
├── main.py                         # Orquestador puro: detecta, calibra y genera JSON
├── scripts/
│   ├── deteccion_piezas.py         # Lógica de detección de piezas (OpenCV)
│   ├── deteccion_referencias.py    # Lógica de detección de cruces de calibración
│   ├── calibracion.py              # Transformación de similitud píxeles → robot
│   └── visualizacion.py            # Dibujo de anotaciones (opcional, solo validación)
├── assets/imagenes/DSC07665.jpg    # Imagen de entrada de ejemplo
├── resultados/                     # Archivos generados
│   ├── imagen1_resultado.jpg       # Imagen anotada en píxeles (solo validación)
│   ├── imagen1_resultado_robot.jpg # Imagen anotada en coordenadas robot (solo validación)
│   ├── deteccion.json              # Datos de detección en píxeles
│   └── datos_robot.json            # Datos transformados al robot (mm)
└── pyproject.toml                  # Dependencias del proyecto
```

## Cómo funciona

El sistema trabaja en varias fases:

1. **Detección por contraste local**  
   Usa un umbral adaptativo para encontrar piezas que contrasten con el fondo, incluso si son oscuras o de color medio.

2. **Detección por saturación (watershed)**  
   Convierte la imagen a HSV y detecta piezas con poca saturación (como tonos beige) que el paso anterior podría perder. El algoritmo *watershed* separa piezas que estén muy juntas o solapadas.

3. **Refinado de contorno**  
   Elimina el fleco de sombra alrededor de cada pieza para que el contorno se ajuste solo al borde real del cerámico.

4. **Deduplicación inteligente**  
   Si una misma pieza fue detectada por los dos métodos anteriores, se elimina el duplicado conservando la detección más precisa.

5. **Propiedades geométricas**  
   Para cada pieza se calcula el rectángulo de área mínima (`minAreaRect`), obteniendo centro, ancho, alto y ángulo. El ángulo se normaliza al rango **(-45°, 45°]**.

6. **Ordenamiento**  
   Las piezas se numeran en orden de lectura: de arriba a abajo y de izquierda a derecha.

## Calibración

El sistema utiliza dos cruces de referencia visibles en la imagen para establecer una **transformación de similitud con reflexión en Y** que convierte píxeles en coordenadas reales del robot (mm). Esto incluye rotación, escala uniforme y la corrección del eje Y (en OpenCV apunta hacia abajo; en el robot apunta hacia arriba).

| Referencia | Píxeles (imagen) | Robot (mm) |
|---|---|---|
| Ref 1 | (≈383, ≈495) | (263.93, -239.43) |
| Ref 2 | (≈2189, ≈2382) | (-363.60, -822.42) |

Las referencias se detectan automáticamente; no es necesario medirlas a mano.

### Fundamento matemático de la calibración

#### 1. Sistemas de coordenadas

- **Imagen (OpenCV)**: origen en la esquina superior izquierda; **x** crece hacia la derecha; **y** crece hacia abajo.
- **Robot**: **x** crece hacia la derecha; **y** crece hacia arriba.

Por tanto, antes de aplicar la rotación entre cámara y robot, debemos reflejar el eje Y de la imagen:

```
X =  x
Y = -y
```

#### 2. Transformación de similitud (rotación + escala uniforme + traslación)

Tras reflejar Y, aplicamos una similitud 2D: rotación `θ` y escala uniforme `s` (la misma para ambos ejes), seguida de una traslación `(tx, ty)`.

```
XR = s·cos(θ)·X − s·sin(θ)·Y + tx
YR = s·sin(θ)·X + s·cos(θ)·Y + ty
```

Sustituyendo `X = x` e `Y = -y`:

```
XR = a·x + b·y + tx
YR = b·x − a·y + ty
```

Donde:
- `a = s·cos(θ)`
- `b = s·sin(θ)`
- `s = √(a² + b²)`  → escala en mm/píxel
- `θ = atan2(b, a)` → rotación de la cámara respecto al robot (tras reflexión en Y)

La matriz afín 2×3 es:

```
| a   b   tx |
| b  -a   ty |
```

#### 3. Obtención de los parámetros a partir de dos puntos

Con dos pares de puntos conocidos (imagen ↔ robot), resolvemos el sistema lineal de 4 ecuaciones y 4 incógnitas (`a`, `b`, `tx`, `ty`).

Sean los vectores de diferencia entre referencias:

- Imagen: `Δu = u₂ − u₁`, `Δv = v₂ − v₁`
- Robot:  `Δx = x₂ − x₁`, `Δy = y₂ − y₁`

Entonces:

```
b = (Δy·Δu + Δx·Δv) / (Δu² + Δv²)
a = (Δx − b·Δv) / Δu          (si Δu ≠ 0)
```

Y las traslaciones:

```
tx = x₁ − a·u₁ − b·v₁
ty = y₁ − b·u₁ + a·v₁
```

#### 4. Conversión de puntos

Para cualquier punto `(px, py)` de la imagen:

```
robot_x = a·px + b·py + tx
robot_y = b·px − a·py + ty
```

#### 5. Conversión de dimensiones

Como la escala es uniforme:

```
ancho_mm = ancho_px · s
alto_mm  = alto_px  · s
```

#### 6. Conversión del ángulo

El ángulo de una pieza no puede copiarse directamente porque depende del sistema de coordenadas. El procedimiento correcto es:

1. Obtener las 4 esquinas del `minAreaRect` en píxeles (`cv2.boxPoints`).
2. Transformar esas 4 esquinas al espacio del robot con la matriz afín.
3. Ejecutar `cv2.minAreaRect` sobre las esquinas transformadas.
4. Normalizar el resultado al rango **(−45°, 45°]**.

Así el ángulo final está referido al eje X del robot y tiene en cuenta tanto la rotación como la reflexión en Y.

## Salidas generadas

### Imágenes anotadas

Sobre la imagen original se dibuja para cada pieza:

| Elemento | Color | Significado |
|---|---|---|
| Contorno rotado | Verde | Borde ajustado de la pieza |
| Centro | Rojo | Punto central con coordenadas |
| Número | Amarillo | Identificador de la pieza |
| Línea ALTO | Naranja | Eje largo de la pieza |
| Línea ANCHO | Cian | Eje corto de la pieza |
| Ángulo | Lila | Valor de rotación en grados |

Se generan dos versiones: una en **píxeles** y otra en **milímetros** del robot.

### `deteccion.json`

Contiene las coordenadas en píxeles de cada pieza detectada:

```json
{
  "imagen": "DSC07665.jpg",
  "total_piezas": 9,
  "piezas": [
    {
      "numero": 1,
      "centro_x": 862,
      "centro_y": 779,
      "ancho": 430,
      "alto": 433,
      "angulo_grados": 7.50
    }
  ]
}
```

### `datos_robot.json`

Contiene las coordenadas transformadas al sistema del robot, junto con los parámetros de calibración usados:

```json
{
  "imagen": "DSC07665.jpg",
  "total_piezas": 9,
  "piezas": [
    {
      "numero": 1,
      "robot_x": 168.09,
      "robot_y": -394.87,
      "ancho_mm": 140.98,
      "alto_mm": 141.96,
      "angulo_grados": -8.35
    }
  ],
  "calibracion": {
    "ref1_px": {"x": 383.59, "y": 493.78},
    "ref1_robot": {"x": 263.93, "y": -239.43},
    "ref2_px": {"x": 2190.08, "y": 2381.15},
    "ref2_robot": {"x": -363.60, "y": -822.42},
    "escala_mm_px": 0.327854,
    "rotacion_grados": -90.85,
    "matriz_afin": {
      "m11": -0.00488, "m12": -0.327818, "m13": 427.67,
      "m21": -0.327818, "m22": 0.00488,  "m23": -116.09
    }
  }
}
```

## Separación entre lógica y visualización

El código está organizado para distinguir claramente:

- **Lógica principal** (obligatoria): `deteccion_piezas.py`, `deteccion_referencias.py`, `calibracion.py` y `main.py` (secciones 1–3). Estos archivos generan los JSON correctamente.
- **Visualización** (opcional): `visualizacion.py` y la sección 4 de `main.py`. Su único propósito es generar las imágenes anotadas para validación humana. Si se eliminan o comentan, el sistema sigue funcionando y produce los JSON exactamente igual.

## Notas importantes

- El sistema está calibrado para piezas de tamaño medio (aproximadamente 300–500 px de lado) sobre fondo claro.
- Si cambias la iluminación o el tipo de pieza, puede ser necesario ajustar los umbrales de saturación (`S > 8`) o el tamaño de bloque del umbral adaptativo (`71×71`).
- El parámetro del watershed (`frac=0.25`) está ajustado para piezas cercanas entre sí; imágenes con piezas muy separadas o muy pegadas pueden necesitar reajuste.
- No se requieren librerías de aprendizaje profundo; todo el procesamiento se realiza con OpenCV de forma determinista.
