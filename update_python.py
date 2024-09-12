import os
import shutil
import subprocess
import sys
import main
import time


from process_utils import ProcessAgent, default_subprocess_options


def download_python(dst_python_dir, messager=None):
    import zipfile

    print("This function is deprecated, Please ask IT to deploy python")
    return

    try:
        os.makedirs(os.path.dirname(dst_python_dir))
    except OSError:
        pass
    python_dir = os.path.join(r'', os.path.basename(dst_python_dir))
    if not os.path.isdir(python_dir):
        python_dir = os.path.join(r'Python3KBR')

    if zipfile.is_zipfile(python_dir + '.zip'):
        def copy():
            if messager:
                messager("COPYING %s -> %s" % (python_dir + '.zip', dst_python_dir + '.zip'))
            shutil.copyfile(python_dir + '.zip', dst_python_dir + '.zip')
            with zipfile.ZipFile(dst_python_dir + '.zip') as pzip:
                pzip.extractall(dst_python_dir)
                result = pzip.filelist[0].filename[:-1]
                if result == os.path.dirname(dst_python_dir):
                    root = os.path.join(dst_python_dir, result)
                    for item in os.listdir(root):
                        shutil.move(os.path.join(root, item), dst_python_dir)
    else:
        def copy():
            if messager:
                messager("COPYING %s -> %s" % (python_dir, dst_python_dir))
            shutil.copytree(python_dir, dst_python_dir)
    copy()


def parse_requirements(repo_root, requirements_file):
    requirements = []
    sub_requirement = ""
    with open(requirements_file) as fd:
        for line in fd:
            line = line.strip(" \n\t")
            if line.strip().startswith('-r'):
                sub_requirement = line[3:]
                requirements += parse_requirements(
                    repo_root, os.path.join(repo_root, sub_requirement)
                )
    if not sub_requirement:
        requirements.append(requirements_file)
    return requirements


def make_python_update_process(
    python_dir, requirements=None, end_callback=None, messager=None
):
    import subprocess

    update_env = os.environ.copy()
    if not requirements:
        requirements = "R:/supamonks/production/homemade_softwares/smks_studio/requirements.txt"
    smks_studio_root = os.path.dirname(requirements)
    update_env["SMKS_STUDIO_ROOT"] = smks_studio_root
    update_env["PYTHONDIR"] = python_dir.replace('/', '\\')
    messager("Updating {} from {}".format(python_dir, requirements))

    requirements = parse_requirements(
        smks_studio_root, os.path.join(smks_studio_root, "requirements.txt")
    )

    if len(requirements) == 1:  # only requirements.txt
        requirements = [
            os.path.join(f, smks_studio_root)
            for f in os.listdir(smks_studio_root)
            if "requirements_" in f
        ]

    processes = []
    for requirement in requirements:
        if "_dev" in requirement or "_standalone" in requirement:
            continue
        env_name = os.path.basename(requirement)
        env_name = "{}_env".format(env_name[len("requirements_"):].rsplit(".", 1)[0])

        process = ProcessAgent(
            [r".\PythonSetupEnv.bat", env_name, requirement],
            dict(env=update_env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT),
            watch_timeout=7, pool=1
        )
        processes.append(process)

    # process = ProcessAgent(
    #     [r".\PythonSetup.bat"],
    #     dict(env=update_env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT),
    #     end_callback=end_callback, pool=1
    # )
    # processes.append(process)
    # shutil.rmtree(os.path.join(python_dir, "smks_env"), ignore_errors=True)
    # shutil.rmtree(os.path.join(python_dir, "maya_env"), ignore_errors=True)

    if processes:
        processes[-1].end_callback = end_callback
    return processes


def install_python(python_dir, reinstall=False, messager=None, end_callback=None, reboot_python=None):
    print("This function is deprecated, Please ask IT to deploy python")
    return

    destination_path = os.path.join(os.path.dirname(python_dir), '_smks_tmp_', os.path.basename(python_dir))
    if os.path.isdir(destination_path):
        shutil.rmtree(destination_path)
    os.makedirs(python_dir, exist_ok=True)
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
        process = subprocess.Popen(command_args, **default_subprocess_options())  # Not windows
    else:
        args = default_subprocess_options()
        si.dwFlags = si.dwFlags | args.get("startupinfo", subprocess.STARTUPINFO()).dwFlags
        process = subprocess.Popen(command_args, startupinfo=si)
    if end_callback:
        end_callback()
    return process
