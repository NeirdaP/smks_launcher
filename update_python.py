import os
import sys


def download_python(dst_python_dir, messager=None):
    import zipfile
    import shutil

    try:
        os.makedirs(os.path.dirname(dst_python_dir))
    except OSError:
        pass
    python_dir = os.path.join(r'I:\bin', os.path.basename(dst_python_dir))
    if not os.path.isdir(python_dir):
        python_dir = os.path.join(r'I:\bin\Python3KBR')

    if zipfile.is_zipfile(python_dir + '.zip'):
        def copy():
            if messager:
                messager("COPYING %s -> %s" % (python_dir + '.zip', dst_python_dir + '.zip'))
            shutil.copyfile(python_dir + '.zip', dst_python_dir + '.zip')
            with zipfile.ZipFile(dst_python_dir + '.zip') as pzip:
                pzip.extractall(os.path.dirname(dst_python_dir))
                result = os.path.join(os.path.dirname(dst_python_dir), pzip.filelist[0].filename[:-1])
            shutil.move(result, dst_python_dir)
    else:
        def copy():
            if messager:
                messager("COPYING %s -> %s" % (python_dir, dst_python_dir))
            shutil.copytree(python_dir, dst_python_dir)
    copy()


def update_python(python_dir, requirements=None, messager=None):
    import subprocess

    update_env = os.environ.copy()
    if not requirements:
        requirements = "P:/DEV/dev/smks_studio/requirements.txt"
    update_env["SMKS_STUDIO_ROOT"] = os.path.dirname(requirements)
    update_env["PYTHONDIR"] = python_dir.replace('/', '\\')
    messager("Updating {} from {}".format(python_dir, requirements))

    process = subprocess.Popen([r".\PythonSetup.bat"], env=update_env, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return process


def install_python(python_dir, reinstall=False, messager=None, end_callback=None, reboot_python=None):
    import subprocess
    import main
    import time
    import shutil

    destination_path = os.path.join(os.path.dirname(python_dir), '_smks_tmp_', os.path.basename(python_dir))
    if os.path.isdir(destination_path):
        shutil.rmtree(destination_path)
    download_python(destination_path, messager=messager)

    command = 'import time; import os; import shutil; import subprocess;'
    if reinstall:
        command += 'time.sleep(4.5);'
    if "I:" not in python_dir and os.path.isdir(python_dir):
        python_tmp = python_dir.replace('\\', '/') + "_old"
        if os.path.isdir(python_tmp):
            shutil.rmtree(python_tmp)
        command += 'os.rename(\"{python}\", \"{python_tmp}\"); shutil.rmtree(\"{python_tmp}\");'.format(
            python=python_dir.replace('\\', '/'), python_tmp=python_tmp
        )
    command += 'os.rename(\"{}\", \"{}\");'.format(destination_path.replace('\\', '/'), python_dir.replace('\\', '/'))
    if reboot_python:
        reboot_python = reboot_python.replace('\\', '/')
        command += 'si = subprocess.STARTUPINFO(); si.dwFlags = subprocess.CREATE_NEW_PROCESS_GROUP;' \
               'subprocess.Popen([r\"{}\", r\"{}\", "update_python"], startupinfo=si);'.format(reboot_python, main.__file__)

    command_args = ["I:/bin/Python3KBR/python.exe" if reinstall else sys.executable, "-c", command]
    messager("Running {}".format(' '.join(command_args)))
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.CREATE_NEW_PROCESS_GROUP
    except (AttributeError, NameError):
        process = subprocess.Popen(command_args)  # Not windows
    else:
        process = subprocess.Popen(command_args, startupinfo=si)
    if end_callback:
        end_callback()
    return process
