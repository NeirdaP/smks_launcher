if __name__ == '__main__':
    import sys
    from qtpy import QtWidgets
    from launcher_dialog import LauncherDialog

    app = QtWidgets.QApplication(sys.argv)

    launcher = LauncherDialog()
    launcher.show()
    # launcher.setTi

    app.exec_()
