# Pruebas de Movimiento, Visión Artificial y Coordinación en Robots UR3e y UR5e

## 1. Descripción general

Este repositorio recoge el conjunto de pruebas y desarrollos realizados durante el Trabajo de Final de Grado relacionados con un sistema colaborativo formado por dos robots colaborativos de Universal Robots (UR3e y UR5e) y una cámara fija de visión artificial.

El objetivo principal del sistema es detectar piezas cerámicas mediante visión artificial, generar trayectorias automáticamente a partir de imágenes y coordinar ambos robots para realizar tareas de manipulación y dibujo sobre las piezas detectadas.

Las pruebas desarrolladas abarcan principalmente:

* Detección de piezas mediante visión artificial
* Extracción de trayectorias desde imágenes
* Generación automática de movimientos robóticos
* Coordinación entre robots colaborativos
* Comunicación TCP/IP entre PC y robots
* Transformación de coordenadas entre referencias
* Detección de superficie mediante sensor de fuerza/par
* Ajuste dinámico de velocidades y aceleraciones
* Generación automática de código URScript
* Simulación de manipulación mediante ventosa

El proyecto no busca implementar una solución industrial cerrada, sino validar y estudiar distintos enfoques de automatización colaborativa aplicados al entorno cerámico.

---

# 2. Organización del repositorio

El repositorio está organizado en distintas versiones (`v1` hasta `v11`), donde cada una representa una evolución progresiva del sistema y de las pruebas realizadas durante el desarrollo del Trabajo de Final de Grado.

```text
Pruebas-TFG/
│
├── v1/
├── v2/
├── v3/
├── v4/
├── v5/
├── v6/
├── v7/
├── v8/
├── v9/
├── v10/
├── v11/
├── v12/
│
└── README.md
```

Cada versión incorpora mejoras relacionadas con:

* Procesado de imagen
* Extracción y simplificación de trayectorias
* Coordinación entre robots
* Generación automática de URScript
* Comunicación TCP/IP
* Gestión de referencias espaciales
* Detección de superficie mediante fuerza
* Escalado dinámico del dibujo
* Simulación de manipulación mediante ventosa

Las últimas versiones (`v10` y `v11`) incorporan las funcionalidades más completas del sistema, incluyendo:

* Detección automática de piezas cerámicas mediante visión artificial
* Selección de la pieza de mayor tamaño
* Adaptación automática del tamaño del dibujo a las dimensiones de la pieza detectada
* Gestión de zonas compartidas entre robots
* Simulación del proceso de recogida y colocación de piezas mediante ventosa en el UR5e
* Coordinación secuencial entre UR5e (manipulación) y UR3e (dibujo)

---

# 3. Arquitectura general del sistema

El sistema sigue una arquitectura modular desarrollada principalmente en Python y URScript.

## 3.1 Flujo principal

1. Captura de imagen desde cámara fija
2. Procesado de imagen mediante OpenCV
3. Detección de bordes y contornos
4. Identificación de piezas cerámicas
5. Selección automática de la pieza principal
6. Escalado dinámico del dibujo
7. Generación de trayectorias
8. Conversión a coordenadas métricas
9. Generación dinámica de URScript
10. Envío de scripts al robot correspondiente
11. Ejecución coordinada entre UR3e y UR5e

---

# 4. Módulos principales

## 4.1 `main.py`

Es el punto de entrada principal del sistema y coordina todo el flujo de ejecución.

Funciones principales:

* Procesado de imagen
* Extracción de trayectorias
* Generación de scripts
* Sincronización entre robots
* Gestión de configuraciones
* Ejecución de pruebas

También permite configurar:

* Robots activos
* IPs y puertos
* Tamaño máximo del dibujo
* Escalado dinámico
* Modo simulación (`dry-run`)
* Robot de referencia

---

## 4.2 `image_processing.py`

Encargado del tratamiento de imagen mediante OpenCV.

Incluye:

* Conversión a escala de grises
* Suavizado Gaussiano
* Detección de bordes con Canny
* Gradiente morfológico
* Filtrado de ruido
* Extracción de contornos

El resultado final es una representación simplificada del dibujo o pieza detectada.

---

## 4.3 `trajectory.py`

Transforma los contornos obtenidos en trayectorias robóticas.

Funciones:

* Simplificación de curvas (`approxPolyDP`)
* Reducción de puntos (`DECIMATE_STEP`)
* Filtrado de trayectorias pequeñas
* Conversión píxel → metro
* Centrado respecto al origen común

También se implementaron límites de tamaño y escalado dinámico dependiendo del tamaño detectado de la pieza cerámica.

---

## 4.4 `vision_detection.py`

Módulo encargado de detectar las piezas cerámicas dentro del espacio de trabajo.

Funciones principales:

* Detección de piezas por contornos
* Cálculo de orientación
* Cálculo de dimensiones
* Selección automática de la pieza más grande
* Obtención de posiciones para manipulación

La cámara utilizada es fija y proporciona una referencia global del sistema.

---

## 4.5 `transform_ur5_to_ur3.py`

Gestiona la transformación entre sistemas de referencia de ambos robots.

Características:

* Definición de un punto común compartido
* Conversión de coordenadas entre bases
* Independencia entre calibraciones
* Gestión del cambio de robot base

Permite que ambos robots interpreten una misma posición física desde referencias diferentes.

---

## 4.6 `urscript_generator_solucion.py`

Generador dinámico de código URScript.

Incluye:

* Movimientos `movej`
* Movimientos `movel`
* Detección de contacto mediante fuerza
* Alturas de seguridad
* Altura de dibujo
* Movimientos suaves y controlados
* Gestión de aceleraciones y velocidades

También incorpora:

* Protección frente a movimientos bruscos
* Gestión de aproximaciones seguras
* Control de subida y bajada del útil

---

## 4.7 `robot_comm.py`

Gestiona la comunicación TCP/IP entre el ordenador y los robots.

Funciones:

* Envío de scripts mediante sockets
* Comunicación con puertos UR
* Servidor TCP en el PC
* Recepción de señales de sincronización
* Ejecución secuencial entre robots

Se utilizan principalmente:

* Puerto `30002` para envío de URScript
* Puerto `50001` para sincronización robot-PC

---

## 4.8 `config_solucion.py`

Archivo central de configuración del sistema.

Contiene:

* Velocidades
* Aceleraciones
* Parámetros de imagen
* Umbrales de fuerza
* Límites geométricos
* Configuración de red
* Alturas de seguridad

Permite ajustar rápidamente el comportamiento global del sistema.

---

# 5. Sistema de referencia y calibración

El sistema utiliza un punto físico compartido entre ambos robots como referencia común.

Aspectos importantes:

* Cada robot mantiene su propio sistema base
* La coordenada Z se detecta individualmente
* La superficie se localiza mediante fuerza/par
* Se evita depender de una calibración rígida global

Esto permite mejorar la robustez del sistema frente a pequeñas variaciones físicas.

---

# 6. Coordinación entre robots

El sistema implementa una coordinación secuencial entre el UR5e y el UR3e para simular un proceso colaborativo de manipulación y dibujo sobre piezas cerámicas.

Funcionamiento general:

1. La cámara fija detecta las piezas cerámicas presentes en la zona de trabajo.
2. Se identifica automáticamente la pieza de mayor tamaño.
3. El UR5e simula la recogida de la pieza mediante una ventosa.
4. El UR5e desplaza la pieza hacia la zona compartida de trabajo.
5. El UR3e realiza el dibujo generado automáticamente a partir de la imagen.
6. El tamaño del dibujo se ajusta dinámicamente al tamaño de la pieza detectada.
7. Una vez finalizado el dibujo, el UR3e envía una señal de finalización.
8. El UR5e continúa el flujo de trabajo correspondiente.

La sincronización entre robots se realiza mediante comunicación TCP/IP a través de un servidor ejecutado en el PC.

---

# 7. Consideraciones importantes de movimiento

Durante las pruebas realizadas se detectaron diversos factores críticos.

## 7.1 Velocidades y aceleraciones

Valores excesivos podían provocar:

* Movimientos bruscos
* Errores de validación
* Paradas de protección

Por ello se ajustaron velocidades reducidas para movimientos de precisión.

---

## 7.2 Número de puntos

Trayectorias demasiado densas producían:

* Sobrecarga del controlador
* Frenadas constantes
* Pérdida de fluidez

Se implementaron técnicas de simplificación de curvas y reducción de puntos.

---

## 7.3 Detección de superficie

La detección de contacto mediante fuerza permitió:

* Ajustar automáticamente la altura de trabajo
* Reducir errores en el dibujo
* Evitar presión excesiva sobre la pieza

---

## 7.4 Zona compartida

Ambos robots trabajan sobre una zona común accesible para los dos.

Fue necesario:

* Ajustar referencias espaciales
* Evitar conflictos de movimiento
* Gestionar esperas y sincronización

---

# 8. Uso del sistema

Ejemplo de ejecución:

```bash
python main.py imagen.jpg
```

Opciones disponibles:

```bash
--dry-run
--seed 42
--base-origen ur3e
--ip3 192.168.X.X
--ip5 192.168.X.X
```

---

# 9. Limitaciones actuales

Actualmente el sistema presenta algunas limitaciones:

* No existe planificación avanzada de colisiones
* Dependencia parcial de calibración manual
* Sensibilidad a parámetros dinámicos
* Variaciones en la detección de fuerza
* Necesidad de ajuste manual en determinadas pruebas

---

# 10. Objetivo del repositorio

Este repositorio tiene como finalidad servir como plataforma experimental para:

* Validar estrategias de coordinación robótica
* Evaluar generación automática de trayectorias
* Analizar comunicación PC-robot
* Estudiar automatización colaborativa aplicada al sector cerámico
* Integrar visión artificial y robótica colaborativa

El proyecto está orientado a investigación, validación técnica y desarrollo experimental dentro del ámbito académico.
