import sys


def main_batch(args):
    import update_python
    import updates

    if "install_python" in args:
        update_python.install_python("C:/software/PythonKBR", reinstall=True).wait()
        update_python.install_python("C:/software/Python3KBR", reinstall=True).wait()
    if "update_smks" in args:
        updates.update_smks_studio("OFFICIAL", "C:/software/smks_studio")


def main_gui(args):
    from qtpy import QtWidgets
    from launcher_dialog import LauncherDialog

    app = QtWidgets.QApplication(args)

    launcher = LauncherDialog()
    launcher.show()

    app.exec_()


if __name__ == '__main__':
    if "-nogui" in sys.argv:
        main_batch(sys.argv)
    else:
        main_gui(sys.argv)
