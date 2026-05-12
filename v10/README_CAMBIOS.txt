VERSION JSON DIRECTO FINAL
==========================

Esta versión se ha preparado para que el proyecto lea el JSON tal cual:

1) vision.py
   - Lee robot_x y robot_y directamente del JSON.
   - Convierte mm a m.
   - No aplica offsets.
   - No calcula centro.
   - No usa ancho/alto para mover.
   - No usa angulo_grados para mover.

2) urscript_generator.py
   - Usa la orientación medida manualmente para coger/devolver piezas:
     UR5E_PICK_ORIENTATION = [2.979, -0.997, 0.0]
   - No usa la orientación del DROP_ZONE para ir a las piezas.
   - No usa el ángulo de visión para girar la muñeca.
   - En el script generado se imprimen los TARGET JSON enviados al robot.

3) main.py
   - Por defecto procesa la pieza 1.
   - Para procesar todas: --pieza 0
   - Para generar sin enviar a robots: --dry-run

Ejemplo:
python main.py --json datos_robot.json --pieza 1 --dry-run

Para robot real:
python main.py --json datos_robot.json --pieza 1
