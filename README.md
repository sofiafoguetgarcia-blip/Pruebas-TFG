# Pruebas de Movimiento, Decoración Cerámica, Visión Artificial y Coordinación en Robots UR3e y UR5e

---

# 1. Descripción general

Este repositorio recoge el conjunto de pruebas, desarrollos y validaciones realizadas durante el Trabajo Fin de Grado relacionadas con una célula colaborativa formada por dos robots colaborativos de Universal Robots (UR3e y UR5e) junto con un sistema de visión artificial de apoyo.

El desarrollo se encuentra vinculado al contexto del proyecto internacional **CERAMIC+**, orientado al estudio de nuevas formas de adaptación tecnológica sobre determinados procesos tradicionales de decoración cerámica.

El objetivo principal del sistema consiste en coordinar distintos elementos de robótica colaborativa para manipular piezas cerámicas y ejecutar automáticamente procesos decorativos, incorporando además herramientas auxiliares capaces de aportar mayor flexibilidad al funcionamiento global desarrollado.

Las pruebas realizadas abarcan principalmente:

- Detección de piezas mediante visión artificial
- Extracción automática de trayectorias desde imágenes
- Adaptación dinámica de patrones decorativos
- Coordinación entre robots colaborativos
- Comunicación TCP/IP entre PC y robots
- Transformación entre referencias espaciales
- Detección automática de superficie mediante fuerza/par
- Ajuste dinámico de velocidades y aceleraciones
- Generación automática de código URScript
- Integración lógica de manipulación mediante sistema de vacío
- Gestión de zonas compartidas de trabajo

El proyecto no busca implementar una solución industrial cerrada, sino validar distintos enfoques relacionados con automatización colaborativa aplicada al entorno cerámico.

---

# 2. Organización del repositorio

El repositorio se organiza en distintas versiones evolutivas desarrolladas a lo largo del Trabajo Fin de Grado.

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
├── v13/
│
└── README.md
```

Cada versión incorpora mejoras progresivas relacionadas con:

- Procesado de imagen
- Simplificación de trayectorias
- Coordinación entre robots
- Comunicación TCP/IP
- Adaptación dinámica del dibujo
- Detección de superficie mediante fuerza
- Gestión de referencias espaciales
- Integración de manipulación mediante vacío
- Generación automática de URScript

Las últimas versiones incorporan las funcionalidades más completas desarrolladas hasta el momento.

---

# 3. Arquitectura general del sistema

El sistema sigue una arquitectura modular desarrollada principalmente en Python y URScript.

## 3.1 Flujo principal

1. Captura de imagen mediante cámara fija
2. Procesado de imagen mediante OpenCV
3. Identificación automática de piezas
4. Selección de pieza objetivo
5. Conversión automática de coordenadas
6. Adaptación dinámica del patrón decorativo
7. Generación de trayectorias
8. Generación automática de URScript
9. Ejecución coordinada entre robots
10. Transferencia de pieza hacia zona compartida
11. Decoración automática
12. Retorno de pieza

---

# 4. Módulos principales

## 4.1 main.py

Punto principal de ejecución del sistema.

Funciones principales:

- Procesado de imagen
- Generación de trayectorias
- Gestión del flujo global
- Sincronización entre robots
- Configuración del sistema
- Coordinación de módulos

Configuraciones principales:

- Robots activos
- IPs y puertos
- Robot base
- Escalado automático
- Límites geométricos
- Parámetros globales

---

## 4.2 image_processing.py

Tratamiento inicial de imagen mediante OpenCV.

Incluye:

- Escala de grises
- Suavizado Gaussiano
- Detección de bordes Canny
- Filtrado de ruido
- Extracción de contornos
- Preparación de trayectorias

---

## 4.3 trajectory.py

Generación y simplificación de trayectorias robóticas.

Funciones:

- Simplificación geométrica
- Reducción de puntos
- Filtrado de trayectorias pequeñas
- Conversión píxel → metro
- Ajuste de coordenadas

---

## 4.4 vision.py

Módulo encargado de interpretar la información obtenida previamente mediante visión artificial.

Funciones principales:

- Lectura del JSON generado
- Selección de pieza objetivo
- Conversión milímetros → metros
- Validación de datos
- Preparación de coordenadas para robótica

El módulo no recalcula geometría ni modifica posiciones detectadas.

Las coordenadas proporcionadas por visión se utilizan directamente durante las etapas posteriores del funcionamiento desarrollado.

---

## 4.5 drawing_scale.py

Módulo encargado de adaptar automáticamente el tamaño del patrón decorativo.

Funciones principales:

- Lectura dimensiones reales
- Cálculo automático de escala
- Adaptación proporcional del dibujo
- Limitación automática de tamaños máximos
- Mantenimiento de proporciones decorativas

Permite mantener una escala adecuada independientemente del tamaño de baldosa detectado.

---

## 4.6 transform_ur5_to_ur3.py

Gestión de referencias compartidas entre robots.

Funciones:

- Punto común de referencia
- Conversión entre sistemas de coordenadas
- Gestión de referencias independientes
- Cambio de robot base

Permite que ambos robots interpreten una misma posición física desde referencias distintas.

---

## 4.7 urscript_generator_solucion.py

Generador dinámico de código URScript.

Incluye:

- movej
- movel
- Alturas de seguridad
- Control de velocidades
- Control de aceleraciones
- Detección de superficie mediante fuerza
- Movimientos suaves
- Aproximaciones seguras

---

## 4.8 robot_comm.py

Gestión de comunicación entre robots y ordenador.

Funciones:

- Comunicación TCP/IP
- Envío de scripts
- Recepción de señales
- Coordinación entre robots
- Gestión de sincronización
- Ejecución secuencial

Puertos utilizados:

- 30002 → envío URScript
- 50001 → sincronización UR5e
- 50002 → sincronización UR3e

---

## 4.9 config_solucion.py

Archivo principal de configuración.

Incluye:

- Velocidades
- Aceleraciones
- Fuerzas límite
- Parámetros de visión
- Configuración red
- Límites geométricos
- Alturas de seguridad

---

# 5. Coordinación entre robots

El sistema implementa una coordinación secuencial entre UR5e y UR3e.

Funcionamiento general:

1. La cámara identifica las piezas presentes.
2. Se selecciona la pieza objetivo.
3. El UR5e realiza la aproximación.
4. Se ejecuta la recogida.
5. El UR5e traslada la pieza.
6. La pieza llega a la zona compartida.
7. El UR3e adapta automáticamente el patrón decorativo.
8. Se realiza el dibujo.
9. El UR3e finaliza.
10. El UR5e recupera la pieza.
11. La pieza vuelve a su posición correspondiente.

La sincronización se realiza mediante TCP/IP y señales de coordinación gestionadas desde el ordenador principal.

---

# 6. Consideraciones importantes

## Velocidades y aceleraciones

Valores excesivos pueden provocar:

- Movimientos bruscos
- Errores de validación
- Paradas de protección

---

## Número de puntos

Trayectorias excesivamente densas pueden producir:

- Sobrecarga de controlador
- Frenadas constantes
- Menor fluidez

---

## Detección de superficie

La detección mediante fuerza permite:

- Ajustar automáticamente alturas
- Reducir errores
- Mejorar estabilidad

---

## Zona compartida

Ambos robots trabajan sobre una misma zona accesible.

Fue necesario:

- Ajustar referencias
- Coordinar tiempos
- Evitar conflictos

---

# 7. Limitaciones actuales

Actualmente todavía existen aspectos futuros de mejora:

- Optimización adicional de tiempos de ciclo
- Validación sobre más patrones decorativos
- Integración física definitiva del sistema de vacío
- Ajustes adicionales sobre determinadas configuraciones dinámicas
- Optimización futura de coordinación avanzada

---

# 8. Objetivo del repositorio

Este repositorio tiene como finalidad:

- Validar estrategias de coordinación robótica
- Evaluar automatización colaborativa
- Analizar integración entre distintos bloques tecnológicos
- Estudiar aplicaciones relacionadas con manipulación y decoración cerámica
- Explorar nuevas posibilidades de adaptación tecnológica sobre procesos tradicionales

El proyecto se encuentra orientado a validación técnica, investigación y desarrollo experimental dentro del ámbito académico.

---
