import urx

ROBOT_IP = "192.168.56.102"  # UR5e

robot = urx.Robot(ROBOT_IP)

try:
    pose = robot.secmon.get_cartesian_info()

    print("\nPOSE TCP ACTUAL:")
    print([
        pose["X"],
        pose["Y"],
        pose["Z"],
        pose["Rx"],
        pose["Ry"],
        pose["Rz"],
    ])

finally:
    robot.close()