# Pruebas de Movimiento y Comunicación en Robots UR3e y UR5e

## 1. Descripción general

Este repositorio recoge un conjunto de pruebas desarrolladas para validar y analizar el comportamiento de dos robots colaborativos de Universal Robots (UR3e y UR5e) en los siguientes aspectos:

* Generación de trayectorias a partir de datos externos (imagen)
* Ejecución de movimientos en espacio cartesiano
* Sincronización entre robots
* Comunicación TCP/IP entre PC y robots
* Estabilidad del sistema ante variaciones de velocidad, aceleración y carga
* Detección de contacto mediante sensor de fuerza/par

El objetivo no es implementar una solución final cerrada, sino explorar y validar distintos enfoques de control, generación de movimiento y coordinación entre robots.

---

## 2. Organización del repositorio

El repositorio está estructurado en distintas versiones (`v1` a `v6`), que representan iteraciones del desarrollo:

```
Pruebas-TFG/
│
├── v1/
├── v2/
├── v3/
├── v4/
├── v5/
├── v6/
│
└── README.md
```

Cada versión introduce modificaciones sobre la anterior, principalmente en:

* Estrategia de generación de trayectorias
* Control de velocidades y aceleraciones
* Gestión de referencias espaciales
* Comunicación entre robots

---

## 3. Arquitectura del sistema

El sistema sigue una arquitectura modular basada en Python, donde cada componente cumple una función específica:

### 3.1. Flujo general

1. Carga de imagen
2. Procesado y detección de bordes
3. Extracción de trayectorias
4. Conversión a coordenadas métricas
5. Reparto de trayectorias entre robots
6. Generación de URScript
7. Envío al UR3e
8. Ejecución y señalización de finalización
9. Envío al UR5e

---

## 4. Módulos principales

### 4.1. `main.py`

Punto de entrada del sistema. Coordina todo el flujo:

* Lectura de argumentos desde terminal
* Procesado de imagen
* Generación de trayectorias
* Reparto entre robots
* Generación de scripts
* Envío y sincronización

Permite configurar parámetros como:

* IP de los robots
* Puerto de comunicación
* Semilla aleatoria
* Ejecución sin envío (`--dry-run`)
* Selección del robot base (`--base-origen`)

---

### 4.2. `image_processing.py`

Encargado del preprocesado de la imagen:

* Conversión a escala de grises
* Filtrado Gaussiano
* Detección de bordes mediante Canny
* Refuerzo de bordes mediante gradiente morfológico

El resultado es una imagen binaria que representa las líneas a seguir.

---

### 4.3. `trajectory.py`

Convierte los bordes en trayectorias:

* Extracción de contornos con OpenCV
* Filtrado de ruido y contornos irrelevantes
* Simplificación de curvas (`approxPolyDP`)
* Reducción de puntos (`DECIMATE_STEP`)
* Conversión de píxeles a metros

Las trayectorias se centran en un sistema de referencia común (0,0).

---

### 4.4. `distributor.py`

Reparte las trayectorias entre UR3e y UR5e:

Criterios:

1. Alcance del UR3e
2. Reparto aleatorio equilibrado

Se garantiza que:

* El UR3e no recibe trayectorias fuera de su alcance
* El UR5e actúa como robot de respaldo

---

### 4.5. `transform_ur5_to_ur3.py`

Gestiona la transformación entre sistemas de referencia:

* Permite definir un punto común del papel
* Convierte poses entre UR3e y UR5e
* Permite elegir el robot base (`ur3e` o `ur5e`)

Esto desacopla la calibración de cada robot.

---

### 4.6. `urscript_generator_solucion.py`

Genera el código URScript:

Incluye:

* Movimiento al origen calibrado
* Detección de superficie mediante fuerza
* Definición de altura de dibujo (`z_dibujo`)
* Ejecución de trayectorias
* Gestión de movimientos seguros

Aspectos relevantes:

* Uso de `movel` para trayectorias
* Uso de `movej` en movimientos globales
* Control explícito de velocidades y aceleraciones

---

### 4.7. `robot_comm.py`

Gestiona la comunicación entre PC y robots:

* Envío de scripts por TCP
* Creación de servidor en el PC
* Recepción de señal de finalización (`LISTO`)
* Ejecución secuencial de robots

Evita que los robots tengan que actuar como servidores.

---

### 4.8. `config_solucion.py`

Define todos los parámetros del sistema:

* Velocidades (`V_DIBUJO`, `V_HOME`, etc.)
* Aceleraciones (`A_DIBUJO`, `A_HOME`)
* Parámetros de imagen
* Límites de trayectorias
* Umbral de fuerza (`F_UMBRAL`)
* Configuración de red

Es el archivo clave para ajustar el comportamiento del sistema.

---

## 5. Sistema de referencia y calibración

El sistema utiliza un **origen común del papel**, pero cada robot lo interpreta en su propio sistema base.

* Cada robot detecta la superficie de forma independiente
* La coordenada Z no es compartida entre robots
* La correspondencia entre robots se basa en un punto calibrado manualmente

Esto evita depender de una calibración global rígida.

---

## 6. Comunicación y sincronización

El sistema utiliza comunicación TCP/IP:

* El PC actúa como servidor
* El UR3e envía un mensaje (`LISTO`) al finalizar
* El UR5e solo se ejecuta después de recibir esa señal

Esto garantiza ejecución secuencial y evita conflictos.

---

## 7. Consideraciones sobre movimiento

Durante las pruebas se han identificado varios factores críticos:

### 7.1. Aceleración

Valores demasiado bajos pueden provocar errores de validación en el controlador.

### 7.2. Número de puntos

Trayectorias demasiado densas generan:

* Movimientos bruscos
* Sobrecarga del controlador

### 7.3. Radio de suavizado (`r`)

Valores muy pequeños provocan:

* Frenadas constantes
* Incremento de esfuerzo dinámico

### 7.4. Alcance del UR3e

El UR3e es más limitado, por lo que:

* Es preferible usarlo como referencia base
* El tamaño del dibujo debe ajustarse

---

## 8. Uso

Ejemplo de ejecución:

```bash
python main.py imagen.jpg
```

Opciones disponibles:

```bash
--dry-run              # Genera scripts sin enviarlos
--seed 42              # Reparto reproducible
--base-origen ur3e     # Define robot base
--ip3 192.168.X.X      # IP UR3e
--ip5 192.168.X.X      # IP UR5e
```

---

## 9. Limitaciones

* No existe planificación de trayectorias avanzada (solo interpolación punto a punto)
* No hay control de colisiones entre robots
* Dependencia de calibración manual
* Sensibilidad a parámetros dinámicos (velocidad/aceleración)

---

## 10. Objetivo del repositorio

Este repositorio sirve como base experimental para:

* Analizar el comportamiento dinámico de robots UR
* Evaluar estrategias de sincronización
* Validar comunicación PC-robot
* Estudiar la generación de trayectorias a partir de datos externos

No está orientado a producción, sino a exploración técnica y pruebas controladas.

---
