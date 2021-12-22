import os

import file
import updates
import subprocess
from qtpy import QtWidgets, QtCore, QtGui


from qt_utils import PathEditor
from smks_news_feed import SmksNewsFeed

_LOCK = False


def watch_process(process, window=None, timeout=-1, end_callback=None):
    global _LOCK
    import time
    import random

    if not process or process.returncode is not None:
        return
    start = time.time()

    try:
        while process and process.poll() is None:
            if (time.time() - start) > timeout > 0:
                raise RuntimeError('Timeout reached: process aborted')
            else:
                time.sleep(0.1)
            while _LOCK:
                time.sleep(0.1)
            _LOCK = True
            for stream in [process.stderr, process.stdout]:
                if not stream:
                    continue
                line = stream.readline()
                if line:
                    line = line[:-1]
                    try:
                        line = line.decode("utf-8")
                    except ValueError:
                        continue
                    if window:
                        low_line = line.lower()
                        if 'error' in low_line or ' end' in low_line or random.randint(0, 3) == 0:
                            window.showMessage(line)
                        else:
                            print(line)
            _LOCK = False
    except OSError:
        print("Cannot fetch outputs of process {}".format(process))
        while process and process.poll() is None:
            if (time.time() - start) > timeout > 0:
                raise RuntimeError('Timeout reached: process aborted')
            else:
                time.sleep(0.1)
    except (IOError, RuntimeError):
        import traceback
        traceback.print_exc()
        process.poll()
        if process and process.returncode is None:
            try:
                process.terminate()
            except OSError:
                pass
        print("Ended with status {}".format(process.returncode))
        return process.returncode
    else:
        out, err = process.communicate()
        if out:
            out = out.decode()
            if window and out:
                window.showMessage(out)
        print(out, err)
    print("Ended with status {}".format(process.returncode))

    if end_callback is not None:
        try:
            end_callback(process.returncode)
        except TypeError as e:
            print(e)
            end_callback()
    return process.returncode


class ProcessWatcher(QtCore.QObject):

    def __init__(self, process, window=None, timeout=-1, end_callback=None):
        super(ProcessWatcher, self).__init__(window)
        self._process = process
        self._window = window
        self._timeout = timeout
        self._end_callback = end_callback
        self._ended = False

        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)

        self._start_time = 0
        self._end_time = 0

    def handle_process_output(self):
        import time
        import random

        global _LOCK

        while _LOCK:
            time.sleep(0.1)
        _LOCK = True

        lines = []

        for stream in [self._process.stderr, self._process.stdout]:
            if not stream:
                continue
            line = stream.readline()
            if line:
                line = line[:-1]
                try:
                    line = line.decode("utf-8")
                except ValueError:
                    continue
                else:
                    lines.append(line)
            else:
                break

        if self._window:
            line = '\n'.join(lines)
            low_line = line.lower()
            if 'error' in low_line or ' end' in low_line or random.randint(0, 3) == 0:
                self._window.showMessage(line)
            else:
                print(line)
        _LOCK = False

    def _end(self):
        self._ended = True
        self._timer.stop()
        self._timer.deleteLater()
        self.deleteLater()

    def _handle_os_error(self):
        import time
        print("Cannot fetch outputs of process {}".format(self._process))
        while self._process and self._process.poll() is None:
            if (time.time() - self._start_time) > self._timeout > 0:
                raise RuntimeError('Timeout reached: process aborted')
        self._end()
        return self._process.returncode or -1

    def _handle_process_error(self):
        import traceback
        traceback.print_exc()
        self._process.poll()
        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
            except OSError:
                pass
        print("Ended with status {}".format(self._process.returncode))
        self._end()
        return self._process.returncode or -1

    def _handle_process_normal_end(self):
        out, err = self._process.communicate()
        if out:
            out = out.decode()
            if self._window and out:
                self._window.showMessage(out)
        print(out, err)
        print("Ended with status {}".format(self._process.returncode))

        if self._process.returncode != 0:
            print("WARNING: Something get wrong with the process {}".format(self._process.pid))

        if self._end_callback is not None:
            try:
                self._end_callback(self._process.returncode)
            except TypeError as e:
                print(e)
                self._end_callback()
        self._end()
        return self._process.returncode

    def watch_process(self):
        import time
        if not self._process:
            raise RuntimeError("Process to watch does not exist !")

        try:
            if self._process.poll() is None:
                if (time.time() - self._start_time) > self._timeout > 0:
                    raise RuntimeError('Timeout reached: process aborted')
                self.handle_process_output()
        except OSError:
            return self._handle_os_error()
        except (IOError, RuntimeError):
            return self._handle_process_error()

        if self._process.returncode is not None:
            return self._handle_process_normal_end()
        self._timer.start(300)

        return None

    def run(self):
        import time
        self._start_time = time.time()
        self._timer.timeout.connect(self.watch_process)
        self._timer.start(30)

    def start(self):
        self.run()

    def is_alive(self):
        return not self._ended


class Thread(QtCore.QThread):

    def __init__(self, target=None, args=None, kwargs=None):
        super(Thread, self).__init__()
        self.target = target
        self._args = args or []
        self._kwargs = kwargs or dict()
        self._ended = False

    def run(self):
        self.target(*self._args, **self._kwargs)
        self._ended = True
        self.exec_()

    def is_alive(self):
        return self.isRunning() and not self._ended

class RequirementsDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(RequirementsDialog, self).__init__(parent)
        # self.main_layout = QtWidgets.QH
        # self.setLayout()


# TODO make configuration window
class LauncherDialog(QtWidgets.QMainWindow):

    SUPA_NETWORK = "https://sites.google.com/supamonks.com/supageneral?pli=1&authuser=1"
    SUPA_NETWORK_DOC = "https://sites.google.com/supamonks.com/workflows/accueil"
    SUPA_DISCORD = "https://discord.gg/armdDJP"
    SUPAMONKS_LETTER = "https://sites.google.com/supamonks.com/supanewsletter/accueil"
    SUPA_TICKET_SUPPORT = "https://www.notion.so/supamonks/Tickets-page-d85b23a15c9947feacf4206ab2eca4d5"
    SUPA_DISCORD_COMMAND = os.path.expanduser('~/AppData/Local/Discord/Update.exe')

    def __init__(self):
        from horoscope import get_today_horoscope
        super(LauncherDialog, self).__init__()
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        QtWidgets.QApplication.instance().setStyle(QtWidgets.QStyleFactory.create("windowsvista"))

        self._process = []
        self._threads = []
        self._smks_process = None
        self._loading_buttons = dict()

        self._tags = []
        self._tags_process = None

        self.python2_path_preset = dict(
            LOCAL='C:/software/PythonKBR',
            SERVER='I:/bin/PythonKBR',
            CUSTOM=None,
        )
        self.python3_path_preset = dict(
            LOCAL='C:/software/Python3KBR',
            SERVER='I:/bin/Python3KBR',
            CUSTOM=None,
        )

        self.setWindowTitle("SMKS Launcher")
        self.background_image = QtGui.QPixmap("images/launcher_background.jpg")
        self._status_bar = self.statusBar()
        self._status_type = ''
        self.settings = QtCore.QSettings("SMKS_Launcher", "Supamonks")
        self._lock_branches = False

        python_group = QtWidgets.QGroupBox("Python")
        self._python_group_toggle_button = QtWidgets.QPushButton()
        self._python_path_preset_choice = QtWidgets.QComboBox()
        self._python2_path_edit = PathEditor(label="Python2 (Maya/Nuke)")
        self._python3_path_edit = PathEditor(label="Python3 (K/Muster/Blender)")
        self._python_install_button = QtWidgets.QPushButton("Install")
        self._python_update_button = QtWidgets.QPushButton("Update")

        self._python_install_button.setObjectName("install_python")
        self._python_update_button.setObjectName("update_python")

        self._requirements_label = QtWidgets.QLabel("Packages")
        self._requirements_preset = QtWidgets.QComboBox()
        self._requirements_path_edit = PathEditor(placeholder="Requirements path")

        update_group = QtWidgets.QGroupBox("Update SMKS Studio")
        self._branch_choice = QtWidgets.QComboBox()
        self._repo_path_edit = PathEditor()
        self._smks_update_button = QtWidgets.QPushButton("Update")
        self._smks_update_button.setObjectName("update_smks_studio")
        self._loading_gif = QtGui.QMovie("./images/loading.gif")
        self._loading_gif.frameChanged.connect(self._update_button_loading_icon)

        self.config_choice = QtWidgets.QComboBox()
        self._run_smks_studio_button = QtWidgets.QPushButton()
        self._run_smks_studio_button.setObjectName("run_smks_studio")

        self._run_smks_letter_button = QtWidgets.QPushButton()
        self._run_smks_letter_button.setObjectName("run_smks_letter")

        self._run_smks_network_button = QtWidgets.QPushButton()
        self._run_smks_network_button.setObjectName("run_smks_network")

        self._status_bar.setMinimumHeight(25)

        self._python_update_button.clicked.connect(self._update_python)
        self._python_install_button.clicked.connect(self._install_python)

        self._python_group_toggle_button.clicked.connect(self.toggle_python_group)
        self._python_path_preset_choice.currentIndexChanged.connect(self.handle_path_preset)
        self._requirements_preset.currentIndexChanged.connect(self.handle_requirements_path_preset)
        self._smks_update_button.clicked.connect(self.update_smks_studio)
        self._run_smks_studio_button.clicked.connect(self.check_n_run_smks_studio)
        self._run_smks_letter_button.clicked.connect(self.open_supa_newsletter)
        self._run_smks_network_button.clicked.connect(self.open_supa_network)

        main_layout = QtWidgets.QVBoxLayout(self.main_widget)
        actions_layout = QtWidgets.QHBoxLayout()
        python_layout = QtWidgets.QVBoxLayout(python_group)
        python_path_layout = QtWidgets.QVBoxLayout()
        requirements_layout = QtWidgets.QHBoxLayout()
        python_buttons_layout = QtWidgets.QHBoxLayout()
        update_layout = QtWidgets.QHBoxLayout(update_group)
        runs_layout = QtWidgets.QHBoxLayout()

        # main_layout.addLayout(actions_layout, 1)
        main_layout.addWidget(python_group, 1)
        main_layout.addStretch()
        main_layout.addWidget(get_today_horoscope(),5)
        main_layout.addWidget(SmksNewsFeed(),3)
        main_layout.addWidget(update_group,1)
        main_layout.addLayout(runs_layout, 2)

        python_layout.addWidget(self._python_path_preset_choice)
        python_layout.addLayout(python_path_layout)
        python_layout.addLayout(requirements_layout)
        python_layout.addWidget(self._requirements_path_edit)
        python_layout.addLayout(python_buttons_layout)
        python_layout.addWidget(self._python_group_toggle_button)
        requirements_layout.addWidget(self._requirements_label, 2)
        requirements_layout.addWidget(self._requirements_preset, 8)
        python_path_layout.addWidget(self._python2_path_edit)
        python_path_layout.addWidget(self._python3_path_edit)
        python_buttons_layout.addWidget(self._python_install_button)
        python_buttons_layout.addWidget(self._python_update_button)

        update_layout.addWidget(self._branch_choice, 5)
        update_layout.addWidget(self._repo_path_edit, 10)
        update_layout.addStretch(2)
        update_layout.addWidget(self._smks_update_button, 5)

        runs_layout.addWidget(self._run_smks_letter_button, 1)
        runs_layout.addWidget(self._run_smks_network_button, 1)
        runs_layout.addWidget(self._run_smks_studio_button, 6)

        self._fetch_tags()

        # ### ICONS ###
        icon = "./images/K.png"

        k_icon = QtGui.QIcon(icon)
        self.setWindowIcon(k_icon)
        self._run_smks_studio_button.setIcon(k_icon)
        self._smks_update_button.setIcon(QtGui.QIcon("images/update.png"))
        self._run_smks_letter_button.setIcon(QtGui.QIcon("images/supamonks_letter.png"))
        self._run_smks_network_button.setIcon(QtGui.QIcon("images/supa_network.png"))

        # https://openapplibrary.org/dev-tutorials/qt-icon-themes
        self._python_group_toggle_button.setIcon(QtGui.QIcon("images/sign-up.png"))

        # ### SIZES ###
        desktop = QtWidgets.QApplication.desktop()
        desktop = desktop.screenGeometry(desktop.screenNumber())

        self._python2_path_edit._label.setMinimumWidth(desktop.width()*0.05)
        self._python3_path_edit._label.setMinimumWidth(desktop.width()*0.05)
        # self._requirements_path._label.setMinimumWidth(desktop.width()*0.05)
        self._run_smks_studio_button.setMinimumHeight(desktop.height()*0.1)
        self._run_smks_letter_button.setMinimumHeight(desktop.height()*0.1)
        self._run_smks_network_button.setMinimumHeight(desktop.height()*0.1)
        self._run_smks_studio_button.setIconSize(QtCore.QSize(desktop.height()*0.05, desktop.height()*0.05))
        self._run_smks_letter_button.setIconSize(QtCore.QSize(desktop.height()*0.03, desktop.height()*0.03))
        self._run_smks_network_button.setIconSize(QtCore.QSize(desktop.height()*0.03, desktop.height()*0.03))
        self._smks_update_button.setMinimumWidth(desktop.height() * 0.09)
        self.resize(int(desktop.width()*0.36), int(desktop.height()*0.2))
        self._python_group_toggle_button.setMaximumHeight(20)

        # ### STYLE ###
        self.apply_style()
        with open('stylesheets/style.css') as fp:
            style_data = fp.read()

        self.setStyleSheet(style_data)
        self._smks_update_button.setStyleSheet("background-color:rgb(125,150,215); color: #EEE;")
        self._run_smks_studio_button.setStyleSheet(
            "QPushButton {border-radius: 5px;}"
            "QPushButton:!hover {background-color:rgb(125,180,136); border: 3px outset rgb(60,90,55);}"
            "QPushButton:hover {background-color:rgb(135,190,145); border: 2px solid palette(highlight);}"
        )
        self._run_smks_letter_button.setStyleSheet(
            "QPushButton:!hover {background-color:rgb(230,230,230); border: 2px outset rgb(155,155,155);}"
            "QPushButton:hover {background-color:rgb(240,240,240); border: 2px solid rgb(255,255,255);}"
        )
        self._run_smks_network_button.setStyleSheet(
            "QPushButton:!hover {background-color:rgb(230,230,230); border: 2px outset rgb(155,155,155);}"
            "QPushButton:hover {background-color:rgb(240,240,240); border: 2px solid rgb(255,255,255);}"
        )

        self._python2_path_edit.setHidden(True)
        self._python3_path_edit.setHidden(True)
        self._requirements_path_edit.setHidden(True)
        self.toggle_python_group()

        if "install_python" in QtWidgets.QApplication.instance().arguments():
            flag_path = os.path.join(os.path.expanduser('~'), ".smks_installed")
            if not os.path.isfile("C:\\.smks_installed") and not os.path.isfile(flag_path):
                open(flag_path, 'w').close()
                QtCore.QTimer.singleShot(1000, self._install_python)
        if "update_python" in QtWidgets.QApplication.instance().arguments():
            QtCore.QTimer.singleShot(1000, self._update_python)
        if "update_smks" in QtWidgets.QApplication.instance().arguments():
            QtCore.QTimer.singleShot(1000, self.update_smks_studio)

    def _handle_branch_changed(self):
        self.update_branches()
        self.settings.setValue("_branch_choice", self._branch_choice.currentText())

    def toggle_python_group(self):
        hide = not self._python_path_preset_choice.isHidden()
        if hide:
            self._python_group_toggle_button.setIcon(QtGui.QIcon("images/sign-down.png"))
        else:
            self._python_group_toggle_button.setIcon(QtGui.QIcon("images/sign-up.png"))
            self.handle_python_path_preset()
            self.handle_requirements_path_preset()

        self._python_path_preset_choice.setHidden(hide)
        self._python_install_button.setHidden(hide)
        self._python_update_button.setHidden(hide)
        self._requirements_label.setHidden(hide)
        self._requirements_preset.setHidden(hide)
        self._repo_path_edit.setHidden(hide)

    def handle_python_path_preset(self):
        hide = self._python_path_preset_choice.currentText() != "CUSTOM"
        self._python2_path_edit.setHidden(hide)
        self._python3_path_edit.setHidden(hide)

    def handle_requirements_path_preset(self):
        hide = self._requirements_preset.currentText() != "CUSTOM"
        self._requirements_path_edit.setHidden(hide)

    def get_repo_path(self):
        repo_path = self._repo_path_edit.get_edited_value().strip()
        if repo_path:
            return repo_path
        else:
            branch = self._branch_choice.currentText()
            if branch == "OFFICIAL" or not branch:
                return "C:/software/smks_studio"
            else:
                return "C:/software/smks_studio_%s" % branch.replace(' ', '_')

    def exit(self):
        import time
        self.showMessage("Reboot...")
        time.sleep(1)
        self.showMessage("Reboot !")
        time.sleep(0.5)
        os._exit(0)

    def showMessage(self, message):
        if self.thread() != QtCore.QThread.currentThread():
            print("WARNING, not the correct thread {}".format(QtCore.QThread.currentThread()))
        print(message)
        message_low = message.lower()
        if 'ended !' in message_low:
            self._status_type = 'ended'
            self._status_bar.setStyleSheet("background-color: rgb(45,156,86);")
        elif 'error' in message_low or ' fail' in message_low:
            self._status_type = 'error'
            self._status_bar.setStyleSheet("background-color: rgb(178,45,86);")
        elif self._status_type:
            self._status_type = ''
            self._status_bar.setStyleSheet("background-color: rgb(53,15,36);")
        if len(message) < 75:
            self._status_bar.showMessage(message)
        else:
            self._status_bar.showMessage("{}...{}".format(message[:50], message[74:]))

    def get_python_paths(self):
        path_preset = self._python_path_preset_choice.currentText()

        if path_preset != "CUSTOM":
            python2_path = self.python2_path_preset.get(path_preset, "C:/software/PythonKBR")
            python3_path = self.python3_path_preset.get(path_preset, "C:/software/Python3KBR")
        else:
            python2_path = self._python2_path_edit.get_edited_value()
            python3_path = self._python3_path_edit.get_edited_value()
        return python2_path, python3_path

    def _install_python(self):
        import sys
        import update_python
        import threading

        if not self._python_update_button.isVisible():
            self.toggle_python_group()

        self._run_smks_studio_button.setEnabled(False)

        self._display_loading(self._python_install_button)

        python2_path, python3_path = self.get_python_paths()
        thread = Thread(target=update_python.install_python, args=[python2_path],
                                  kwargs=dict(reinstall=True, messager=self.showMessage))
        self._threads.append(thread)
        thread.start()
        reboot = python3_path.lower() in sys.executable.replace('\\', '/').lower()
        thread = Thread(target=update_python.install_python, args=[python3_path],
                                  kwargs=dict(reinstall=reboot, messager=self.showMessage,
                                              end_callback=self.exit if reboot else self._handle_install_end,
                                              reboot_python=os.path.join(python3_path, "python") if reboot else None))
        self._threads.append(thread)
        QtCore.QTimer.singleShot(3000, thread.start)

    def _update_python(self, end_callback=None):
        import functools

        if not self._python_update_button.isVisible():
            self.toggle_python_group()

        self._display_loading(self._python_update_button)

        requirements_path = self.get_requirements_path()
        if not os.path.isfile(requirements_path):  # if requirements is not ready shift python update
            self.update_smks_studio(end_callback=self._update_python)
            return

        python2_path, python3_path = self.get_python_paths()
        QtCore.QTimer.singleShot(
            100, functools.partial(self._update_python2, python2_path, requirements_path)
        )
        QtCore.QTimer.singleShot(
            7000, functools.partial(self._update_python3, python3_path, requirements_path, end_callback)
        )

    def _update_python2(self, python2_path, requirements_path, end_callback=None):
        import update_python

        if not os.path.isdir(python2_path):
            thread = Thread(target=update_python.install_python, args=[python2_path],
                                      kwargs=dict(messager=self.showMessage))
            self._threads.append(thread)
            thread.start()
        else:
            process = update_python.update_python(python2_path, messager=self.showMessage,
                                                  requirements=requirements_path)
            watcher = ProcessWatcher(process, window=self, end_callback=end_callback)
            watcher.start()
            self._process.append(process)
            self._threads.append(watcher)
        self.update_last_packages_update()

    def _update_python3(self, python3_path, requirements_path, end_callback=None):
        import sys
        import update_python

        if not os.path.isdir(python3_path):
            reboot = python3_path.lower() in sys.executable.replace('\\', '/').lower()
            thread = Thread(target=update_python.install_python, args=[python3_path],
                                      kwargs=dict(reinstall=reboot, messager=self.showMessage,
                                                  end_callback=end_callback or (self.exit if reboot else self._handle_update_end),
                                                  reboot_python=os.path.join(python3_path,
                                                                             "python") if reboot else None))
            self._threads.append(thread)
            thread.start()
        else:
            process = update_python.update_python(python3_path, messager=self.showMessage,
                                                  requirements=requirements_path)
            watcher = ProcessWatcher(process, window=self, end_callback=end_callback or self._handle_update_end)
            watcher.start()
            self._process.append(process)
            self._threads.append(watcher)
        self.update_last_packages_update()

    def get_requirements_path(self, update=True):
        requirement_preset = self._requirements_preset.currentText()
        if requirement_preset == "CUSTOM":
            return self._requirements_path_edit.get_edited_value()
        if requirement_preset == "DEFAULT":
            return os.path.join(self.get_repo_path(), "requirements.txt")
        return "P:/DEV/dev/smks_studio/requirements.txt"

    def _update_button_loading_icon(self):
        for button, icon, stylesheet in list(self._loading_buttons.values()):
            # prevent list changing during update
            if button.property("loading"):
                button.setIcon(self._loading_gif.currentPixmap())

    def _display_loading(self, button):
        button.setProperty("loading", True)
        if not button.objectName() in self._loading_buttons:
            self._loading_buttons[button.objectName()] = (button, button.icon(), button.styleSheet())
        self._loading_gif.start()
        button.setStyleSheet("background: rgb(35,90,150);")

    def _hide_loading(self, button):
        button.setProperty("loading", False)
        button_id = button.objectName()
        try:
            button, icon, stylesheet = self._loading_buttons[button_id]
        except KeyError:
            return
        else:
            del self._loading_buttons[button_id]
            button.setIcon(icon)
            button.setStyleSheet(stylesheet)

        if not self._loading_buttons:
            self._loading_gif.stop()

    def update_data(self):
        import update_smks
        self._python_path_preset_choice.addItem("LOCAL")
        self._python_path_preset_choice.addItem("SERVER")
        self._python_path_preset_choice.addItem("CUSTOM")

        self.handle_python_path_preset()

        self._requirements_preset.addItem("DEFAULT")
        self._requirements_preset.addItem("SERVER")
        self._requirements_preset.addItem("CUSTOM")

        self.config_choice.addItem("")
        self.config_choice.addItem("BETA")

        self.handle_requirements_path_preset()

        self._python2_path_edit.set_value("C:/software/PythonKBR")
        self._python3_path_edit.set_value("C:/software/Python3KBR")
        self._repo_path_edit._path_line_edit.setPlaceholderText("Install path (automatic if empty)")

        self.update_branches()

        current_branch = self.settings.value("_branch_choice", "OFFICIAL")

        try:
            self._branch_choice.setCurrentText(current_branch)
        except AttributeError:  # PySide compatibility
            pass
        else:
            self._branch_choice.currentTextChanged.connect(self._handle_branch_changed)

    def _fetch_tags(self):
        import update_smks

        if self._tags:
            return self._tags

        if not self._tags_process:
            repo_path = self.get_repo_path()
            if repo_path and os.path.isdir(self.get_repo_path()):
                subprocess.call([update_smks.get_git(), 'fetch'], cwd=self.get_repo_path())
                self._tags_process = subprocess.Popen([update_smks.get_git(), 'tag'], stdout=subprocess.PIPE,
                                                        stderr=subprocess.PIPE, cwd=self.get_repo_path())
                ProcessWatcher(self._tags_process, self, end_callback=self._fetch_tags).start()
        else:
            if self._tags_process.poll() is not None:
                out, err = self._tags_process.communicate()
                self._tags = out.decode().split('\n')
                self.showMessage("")
        return self._tags

    def update_branches(self):
        if self._lock_branches:
            return
        self._lock_branches = True

        icons = dict(
            OFFICIAL="./images/supa.png",
            BETA="./images/build.png"
        )

        for choice in updates.get_branches().keys():
            if self._branch_choice.findText(choice) >= 0:
                continue
            if choice in icons:
                self._branch_choice.addItem(QtGui.QIcon(icons[choice]), choice)
            else:
                self._branch_choice.addItem(choice)

        tags = self._fetch_tags()
        for tag in tags:
            if self._branch_choice.findText(tag) >= 0:
                continue
            if tag in icons:
                self._branch_choice.addItem(QtGui.QIcon(icons[tag]), tag)
            else:
                self._branch_choice.addItem(tag)
        self._lock_branches = False

    def apply_style(self, widget=None):
        widget = widget or QtWidgets.QApplication.instance()

        settings = QtCore.QSettings(self)

        id = QtGui.QFontDatabase.addApplicationFont("./font/lexend.ttf")
        font = QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(id)[0], 9)
        font = settings.value('font', font)
        widget.setFont(font)

        if settings.value('style', ''):
            QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create(settings.value('style')))

        settings.beginGroup('colors')

        # setup the palette
        palette = QtWidgets.QApplication.palette()
        # A color to indicate a selected item or the current item. By default, the highlight color is Qt.darkBlue.
        palette.setColor(QtGui.QPalette.Highlight, settings.value('highlight', QtGui.QColor("#ad4e5c")))
        palette.setColor(QtGui.QPalette.HighlightedText, settings.value('highlighted_text', QtGui.QColor("#42314a")))
        palette.setColor(QtGui.QPalette.WindowText, settings.value('window_text', QtGui.QColor("#b9c2c8")))
        palette.setColor(QtGui.QPalette.Window, settings.value('window', QtGui.QColor("#3e4041")))
        palette.setColor(QtGui.QPalette.Text, settings.value('text', QtGui.QColor("#998888")))
        palette.setColor(QtGui.QPalette.Base, settings.value('base', QtGui.QColor("#2b2b2b")))
        palette.setColor(QtGui.QPalette.Dark, settings.value('dark', QtGui.QColor("#22222b")))
        palette.setColor(QtGui.QPalette.Light, settings.value('light', QtGui.QColor("#151515")))
        palette.setColor(QtGui.QPalette.Midlight, settings.value('midlight', QtGui.QColor("#911f36")))
        palette.setColor(QtGui.QPalette.Mid, settings.value('mid', QtGui.QColor("#4b1b1f")))
        palette.setColor(QtGui.QPalette.Button, settings.value('button', QtGui.QColor("#322F2F")))
        palette.setColor(QtGui.QPalette.ButtonText, settings.value('button_text', QtGui.QColor("#a9b7c6")))

        settings.endGroup()

        widget.setPalette(palette)

    def handle_path_preset(self):
        hidden = self._python_path_preset_choice.currentText() != "CUSTOM"
        self._python2_path_edit.setHidden(hidden)
        self._python3_path_edit.setHidden(hidden)

        enabled = self._python_path_preset_choice.currentText() != "SERVER"
        self._python_install_button.setEnabled(enabled)
        self._python_update_button.setEnabled(enabled)

    def _handle_smks_update_end(self, return_code=0):
        self.update_branches()
        self._hide_loading(self._smks_update_button)

    def _handle_install_end(self):
        self._hide_loading(self._python_install_button)
        self.showMessage("Install Ended !")
        self._run_smks_studio_button.setEnabled(True)
        QtCore.QTimer.singleShot(500, self._update_python)

    def _handle_update_end(self, return_code=0):
        self._hide_loading(self._python_update_button)
        if return_code != 0:
            self.showMessage("ERROR: Update Failed !")
        else:
            self.showMessage("Update Ended !")

    def update_smks_studio(self, end_callback=None):
        repo_path = self.get_repo_path()
        process = updates.update_smks_studio(self._branch_choice.currentText(), repo_path)

        if end_callback:
            end_callback = lambda return_code, callback=end_callback: callback() and self._handle_smks_update_end()
        else:
            end_callback = self._handle_smks_update_end

        watcher = ProcessWatcher(process, window=self, end_callback=end_callback)
        watcher.start()

        self._process.append(process)
        self._threads.append(watcher)
        self._display_loading(self._smks_update_button)

    def ask_update(self):
        update_ask_dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, "Update ?",
                                                  "Seems there are available updates",
                                                  QtWidgets.QMessageBox.NoButton, self)
        update_ask_dialog.setStyleSheet("QPushButton{background:rgba(85,85,85);}")
        update_button = update_ask_dialog.addButton("Yes, Do it steup !", QtWidgets.QMessageBox.ApplyRole)
        update_button.setStyleSheet("background-color:rgb(125,185,136); color: #FFF;")
        update_button.setIcon(QtGui.QIcon("./images/update.png"))
        update_ask_dialog.addButton("Later, Run it Gros !", QtWidgets.QMessageBox.NoRole)

        update_ask_dialog.exec_()
        return update_ask_dialog.clickedButton() is update_button

    def get_last_packages_update(self):
        launcher_data_folder = file.get_os_data_path("smks_launcher")

        try:
            os.makedirs(launcher_data_folder)
        except OSError:
            pass

        update_file = os.path.join(launcher_data_folder, "requirements_last_update")

        if not os.path.isfile(update_file):
            return 0

        with open(update_file) as fp:
            return int(fp.read())

    def update_last_packages_update(self):
        import update_smks
        launcher_data_folder = file.get_os_data_path("smks_launcher")

        try:
            os.makedirs(launcher_data_folder)
        except OSError:
            pass

        log_process = subprocess.Popen([update_smks.get_git(), "log", "-1", "--format=%at", "requirements.txt"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.get_repo_path())
        out, err = log_process.communicate()

        update_file = os.path.join(launcher_data_folder, "requirements_last_update")
        with open(update_file, 'wb') as fp:
            fp.write(out)

    def check_n_run_smks_studio(self):
        import update_smks
        import functools
        import shutil
        import utils

        self._display_loading(self._run_smks_studio_button)

        repo_path = self.get_repo_path().replace('/', os.path.sep)
        python_path = os.path.join(repo_path, "smks_studio_home", "python")
        third_party = os.path.join(python_path, "third_party")

        try:
            if not os.path.isdir(os.path.join(third_party, "kabaret.blender_session", "src", "kabaret")):
                raise ImportError("No blender session")
            if not os.path.isdir(os.path.join(third_party, "smks_core")):
                raise ImportError("No SMKS Core")
            if not os.path.isdir(python_path):
                raise ImportError("No smks_studio")
        except (subprocess.CalledProcessError, ImportError):
            import traceback
            traceback.print_exc()
            print(python_path)
            if os.path.isdir(os.path.join(third_party, "kabaret.blender_session")):
                shutil.rmtree(os.path.join(third_party, "kabaret.blender_session"))
            if os.path.isdir(os.path.join(third_party, "smks_core")):
                shutil.rmtree(os.path.join(third_party, "smks_core"))
            if self.thread() == QtCore.QThread.currentThread():
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Need Update",
                                  "Some modules should be downloaded before running SMKS Studio",
                                  QtWidgets.QMessageBox.Ok, self).exec_()
            QtCore.QTimer.singleShot(500, functools.partial(self.update_smks_studio, self.check_n_run_smks_studio))
            return

        fetch_process = subprocess.Popen([update_smks.get_git(), 'fetch'], cwd=self.get_repo_path())
        fetch_process.wait()
        status_process = subprocess.Popen([update_smks.get_git(), "status"], stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, cwd=self.get_repo_path())
        out, err = status_process.communicate()
        if b"is behind" in out:
            answer = self.ask_update()
            if answer:
                QtCore.QTimer.singleShot(500, functools.partial(self.update_smks_studio, self.check_n_run_smks_studio))
                return

        package_last_update = self.get_last_packages_update()

        log_process = subprocess.Popen([update_smks.get_git(), "log", "-1", "--format=%at", "requirements.txt"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.get_repo_path())
        out, err = log_process.communicate()
        requirements_last_update = int(out)
        if requirements_last_update != package_last_update:
            if self.thread() == QtCore.QThread.currentThread():
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Need Update",
                                  "Some package needs update", QtWidgets.QMessageBox.Ok, self).exec_()
            QtCore.QTimer.singleShot(500, functools.partial(self._update_python, self.run_smks_studio))
            return

        self.run_smks_studio()

    def run_smks_studio(self, *args):  # *args for callback
        import os
        import functools

        self._display_loading(self._run_smks_studio_button)

        for process in self._process:
            process.poll()

        self._process = [process for process in self._process if process.returncode is None]
        self._threads = [thread for thread in self._threads if thread.is_alive()]

        if self._process or self._threads:
            QtCore.QTimer.singleShot(1000, self.run_smks_studio)
            self._run_smks_studio_button.setEnabled(False)
            return

        python_path = os.path.join(self.get_repo_path().replace('/', '\\'), "smks_studio_home", "python")

        smks_studio_env = os.environ.copy()
        smks_path = self.get_repo_path()
        smks_studio_env["SMKS_STUDIO_ROOT"] = str(smks_path)

        py2_path, py3_path = self.get_python_paths()
        smks_studio_env["PYTHONDIR"] = py3_path.replace('/', '\\')
        smks_studio_env["PYTHON2DIR"] = py2_path.replace('/', '\\')
        smks_studio_env["PYTHON3DIR"] = py3_path.replace('/', '\\')
        smks_studio_env["CONFIG"] = self.config_choice.currentText()

        subprocess.Popen(['cmd', '/C', 'setx', 'PYTHONDIR', py3_path.replace('/', '\\')], shell=True)
        subprocess.Popen(['cmd', '/C', 'setx', 'PYTHON2DIR', py2_path.replace('/', '\\')], shell=True)
        subprocess.Popen(['cmd', '/C', 'setx', 'PYTHON3DIR', py3_path.replace('/', '\\')], shell=True)

        try:
            user_path = os.environ["USERPROFILE"]
        except KeyError:
            user_path = os.path.expanduser('~')

        self._hide_loading(self._python_update_button)
        QtCore.QTimer.singleShot(4000, self._handle_smks_runned)
        self._smks_process = subprocess.Popen([os.path.join(os.path.dirname(__file__), "Run_smks_studio.bat")],
                         env=smks_studio_env, shell=True, cwd=user_path)

    @classmethod
    def open_supa_network(cls):
        os.startfile(cls.SUPA_NETWORK)

    @classmethod
    def open_supa_newsletter(cls):
        os.startfile(cls.SUPAMONKS_LETTER)

    def _handle_smks_runned(self):
        self._run_smks_studio_button.setEnabled(True)
        if self._smks_process:
            self._smks_process.poll()
            if self._smks_process and self._smks_process.returncode is not None and self._smks_process.returncode != 0:
                QtCore.QTimer.singleShot(500, self._update_python)
                QtCore.QTimer.singleShot(10000, self.run_smks_studio)
            else:
                self._hide_loading(self._smks_update_button)
                self._hide_loading(self._run_smks_studio_button)
        else:
            self._hide_loading(self._run_smks_studio_button)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.width(), self.height(), self.background_image)
        super(LauncherDialog, self).paintEvent(event)

    def showEvent(self, event):
        super(LauncherDialog, self).showEvent(event)
        QtCore.QTimer.singleShot(50, self.update_data)
        self.background_image = self.background_image.copy(QtCore.QRect(QtCore.QPoint(0, 0), self.size()))
        self._smks_update_button.setIconSize(QtCore.QSize(self._smks_update_button.height() * 0.5, self._smks_update_button.height() * 0.5))
        new_pos = self.pos()
        new_pos.setY(max(50, new_pos.y() - 200))
        self.move(new_pos)

    def closeEvent(self, event):
        QtWidgets.QApplication.instance().exit(0)
