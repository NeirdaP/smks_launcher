import os
import shutil
import subprocess

import utils

GIT_EXE = 'git'
GIT_CHECKED = False
SMKS_REPO_LINK = "https://supamonks:supamonk09,@gitlab.com/smks/smks_studio.git"


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


if __name__ == '__main__':
    import sys
    import time

    git = get_git()

    args = parse_command_line_args(sys.argv)
    repo_path = args['repo_path']
    try:
        original_credential = subprocess.check_output(
            [git, "config", "--global", "credential.helper"]
        ).strip().strip(b'\n')
    except subprocess.CalledProcessError:
        original_credential = ""
    subprocess.check_call(
        [git, "config", "--global", "credential.helper", ""]
    )

    if not os.path.isdir(args['python_path']):
        try:
            os.makedirs(repo_path)
        except OSError:
            pass
        print("Downloading SMKS Studio...")
        subprocess.check_call(
            [git, "clone", "-q", SMKS_REPO_LINK, repo_path]
        )
    branch = args['branch']
    try:
        subprocess.check_call([git, "checkout", branch], cwd=repo_path)
    except subprocess.CalledProcessError:
        import traceback
        traceback.print_exc()
        exit(1)
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

    success = False
    for i in range(2):
        try:
            print("Update Submodules...")
            subprocess.check_call([git, "submodule", "update", "--init"], cwd=repo_path)
        except:
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
        subprocess.check_call([git, "submodule", "init"], cwd=repo_path)
        subprocess.check_call([git, "submodule", "update", "--init", "--remote"], cwd=repo_path)

    process = subprocess.Popen([git, "submodule", "update", "--remote", "--merge", "--quiet",
                                "smks_studio_home/python/third_party/smks_core"],
                               cwd=repo_path)
    process.wait()
    subprocess.check_call(
        [git, "config", "--global", "credential.helper", original_credential]
    )
    print("Update Ended !")
