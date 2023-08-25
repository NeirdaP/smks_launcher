import os
import shutil
import subprocess
import zipfile

import utils

GIT_EXE = 'git'
GIT_CHECKED = False
SMKS_REPO_LINK = "http://supamonks:supamonk09,@supa-git.supamonks.lan/smks/smks_studio.git"
SMKS_BACKUP_ZIP = r"I:\PIPE\smks_studio.zip"


def get_git():
    global GIT_EXE
    global GIT_CHECKED

    if not GIT_CHECKED:
        try:
            process = subprocess.Popen([GIT_EXE], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            result = utils.wait_process(process, 2)
            if result is None:
                raise RuntimeError("Timed Out!")
        except (RuntimeError, OSError):
            if os.path.isdir(r"C:\software\Git\bin"):
                os.environ["PATH"] = os.environ["PATH"] + r";C:\software\Git\bin"
                GIT_EXE = r"C:\software\Git\bin\git"
            elif os.path.isdir(r"C:\Program Files\Git\bin"):
                os.environ["PATH"] = os.environ["PATH"] + r";C:\Program Files\Git\bin"
                GIT_EXE = r"C:\Program Files\Git\bin\git"
            else:
                os.environ["PATH"] = os.environ["PATH"] + r";I:\bin\Git\PortableGit\bin"
                GIT_EXE = r"I:\bin\Git\PortableGit\bin\git"
        except subprocess.CalledProcessError:
            pass
        GIT_CHECKED = True
    return GIT_EXE


def parse_command_line_args(args):
    import argparse

    repo_path = "C:/software/DEV/smks_studio"
    branch = 'MASTER'

    parser = argparse.ArgumentParser(
        description='Smks Update'
    )

    parser.add_argument(
        '-B', '--branch', default=branch, dest='branch', help='repo branch'
    )

    parser.add_argument(
        '-p', '--repo_path', default=repo_path, dest='repo_path', help='Cluster Host address'
    )

    values, remaining_args = parser.parse_known_args(args)
    return dict(
        branch=values.branch,
        repo_path=values.repo_path,
        python_path=values.repo_path + "/smks_studio_home/python",
        args=remaining_args
    )


def default_subprocess_options():
    popen_kwargs = dict()
    if sys.platform == "win32":
        # This hides the console window if pythonw.exe is used
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        popen_kwargs["startupinfo"] = startupinfo
    return popen_kwargs


def _fix_supa_url(repo_path):
    modules_path = os.path.join(repo_path, ".gitmodules")

    if os.path.isfile(modules_path):
        with open(modules_path, 'r') as fp:
            modules_content = fp.read()

        if ".local" in modules_content:
            modules_content = modules_content.replace(".supamonks.local", ".supamonks.lan")
            modules_content = modules_content.replace("supa-git/", "supa-git.supamonks.lan/")

            with open(modules_path, 'w') as fp:
                fp.write(modules_content)

            remote_process = subprocess.Popen(
                [get_git(), "submodule", "sync"], cwd=repo_path,
                stdout=subprocess.PIPE
            )
            remote_process.wait()


if __name__ == '__main__':
    import sys
    import time

    args = parse_command_line_args(sys.argv)
    repo_path = args['repo_path']

    try:
        subprocess.check_call(["ping", "-n", "2", "supa-git.supamonks.lan"], shell=True, **default_subprocess_options())
    except subprocess.CalledProcessError:
        print("ERROR: Cannot connect to supa-git")
        time.sleep(2)
        print("Using", SMKS_BACKUP_ZIP)
        repo_file = os.path.join(os.path.dirname(repo_path), os.path.basename(SMKS_BACKUP_ZIP))
        shutil.copyfile(SMKS_BACKUP_ZIP, repo_file)
        with zipfile.ZipFile(repo_file, 'r') as zip_ref:
            zip_ref.extractall(repo_path)
        if os.path.isdir(repo_path) and os.listdir(repo_path):
            print("SUCCESS !")
            exit(0)
        else:
            print("ERROR !")
            exit(-1)

    git = get_git()

    config_process1 = subprocess.Popen(
        [git, "config", "--global", "credential.helper"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **default_subprocess_options()
    )
    config_process2 = subprocess.Popen(
        [git, "config", "--system", "credential.helper"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **default_subprocess_options()
    )

    config_process1.wait()
    config_process2.wait()

    original_credential = config_process1.stdout.read().strip() or config_process2.stdout.read().strip()

    subprocess.check_call(
        [git, "config", "--global", "credential.helper", ""]
    )
    subprocess.call([
        git, "config", "--global", "--unset", "http.sslCAInfo"
    ])
    subprocess.check_call([
        git, "config", "--global", "http.https://supa-git.supamonks.lan.sslCAInfo", r"P:\DEV\SUPA-GIT.SUPAMONKS.download.crt"
    ])
    subprocess.check_call([
        git, "config", "--global", "http.sslBackend", r"openssl"
    ])
    if not os.path.isdir(args['python_path']):
        try:
            os.makedirs(repo_path)
        except OSError:
            pass
        print("Downloading SMKS Studio...")
        try:
            subprocess.check_output(
                [git, "clone", "-q", SMKS_REPO_LINK, repo_path],
            )
            subprocess.check_call([git, "config", "--global", "--add", "safe.directory", repo_path])
        except subprocess.CalledProcessError as e:
            print(e, e.cmd)
            subprocess.check_call(
                [git, "config", "--global", "credential.helper", original_credential]
            )
            raise

    branch = args['branch']
    try:
        subprocess.check_call([git, "config", "--global", "--add", "safe.directory", repo_path])
        subprocess.check_call([git, "checkout", branch], cwd=repo_path)
    except subprocess.CalledProcessError:
        import traceback
        traceback.print_exc()
        subprocess.check_call(
            [git, "config", "--global", "credential.helper", original_credential]
        )
        raise RuntimeError("Cannot switch branch {}".format(branch))
    sys.stdout.flush()
    time.sleep(0.5)

    try:
        os.remove(os.path.join(repo_path, ".git/index.lock"))
    except OSError:
        pass

    success = False
    for i in range(2):
        try:
            print("Update...")
            subprocess.check_call([git, "checkout", "*"], cwd=repo_path)
            return_code = subprocess.check_call([git, "pull", "-q", "--strategy-option=theirs", "origin", branch],
                                                cwd=repo_path)
            subprocess.check_call([git, "pull", "-q", "--strategy-option=theirs", "origin", "--quiet", branch],
                                  cwd=repo_path)
        except:
            sys.stderr.flush()
            shutil.rmtree(repo_path)
            success = False
        else:
            sys.stdout.flush()
            success = True
            break

    if not success:
        raise RuntimeError("Update failed!")
    _fix_supa_url(repo_path)

    success = False
    for i in range(2):
        try:
            print("Update Submodules...")
            out = subprocess.check_output(
                args=[git, "submodule", "sync"],
                cwd=repo_path, stderr=subprocess.STDOUT
            )
            print(out)
            out = subprocess.check_output(
                args=[git, "submodule", "update", "--init"],
                cwd=repo_path, stderr=subprocess.STDOUT
            )
            print(out)
        except subprocess.CalledProcessError as e:
            print("Error on update", e.stdout, e.stderr)
            success = False
            third_party = os.path.join(repo_path, "smks_studio_home/python/third_party")
            for sub_module in os.listdir(third_party):
                sub_module = os.path.join(third_party, sub_module)
                if os.path.isdir(sub_module):
                    shutil.rmtree(sub_module)
        except Exception as e:
            print("Error on update")
            success = False
        else:
            success = True
            break

    if not success:
        third_party_folder = os.path.join(repo_path, "smks_studio_home/python/third_party")
        for folder in os.listdir(third_party_folder):
            if os.path.isdir(os.path.join(third_party_folder, folder)):
                shutil.rmtree(os.path.join(third_party_folder, folder))
        subprocess.call([git, "submodule", "init"], cwd=repo_path)
        subprocess.check_call([git, "submodule", "sync"], cwd=repo_path)
        subprocess.call([git, "submodule", "update", "--init", "--remote"], cwd=repo_path)

    process = subprocess.Popen([git, "submodule", "update", "--remote", "--merge", "--quiet"],
                               cwd=repo_path)
    process.wait(8)

    subprocess.check_call(
        [git, "config", "--global", "credential.helper", "wincred"]
    )
    print("Update Ended !")


def get_current_branch(repo_path):
    branch_process = subprocess.Popen(
        [get_git(), "branch"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=repo_path,
    )
    out, err = branch_process.communicate()
    branch = out.decode("utf-8").split("\n")
    branch = next(b for b in branch if b.startswith('*'))
    branch = branch[2:].strip(" \n\r")
    return branch
