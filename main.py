import ctypes
import os
import sys


def main_batch(args):
    import update_python
    import updates

    if "install_python" in args and not os.path.isdir("C:/software/Python3KBR/python"):
        update_python.install_python("C:/software/PythonKBR", reinstall=True).wait()
        update_python.install_python("C:/software/Python3KBR", reinstall=True).wait()
    if "update_smks" in args:
        updates.update_smks_studio("OFFICIAL", "C:/software/smks_studio")


def main_gui(args):
    from qtpy import QtWidgets
    from launcher_dialog import LauncherDialog

    app = QtWidgets.QApplication(args)
    app.setApplicationName("Smks Launcher")
    app.setOrganizationName("Supamonks")

    try:
        # make windows handle the process separately from other
        # python process
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "{}.{}.valid".format(
                QtWidgets.QApplication.organizationName(),
                QtWidgets.QApplication.applicationName()
            )
        )
    except AttributeError:
        pass

    launcher = LauncherDialog()
    launcher.show()

    app.exec_()


if __name__ == '__main__':
    if "-nogui" in sys.argv:
        main_batch(sys.argv)
    else:
        main_gui(sys.argv)
