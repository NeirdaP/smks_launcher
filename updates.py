import os

BRANCHES = dict(
)


def get_branches():
    import json
    import logging
    import os

    branches = BRANCHES.copy()
    if os.path.isfile("./branches.json"):
        with open('./branches.json') as fp:
            branches.update(json.load(fp))
    else:
        logging.getLogger("smks_launcher").warning("There is no branches.json")

    return branches


def update_smks_studio(branch=None, repo_path=None):
    import update_smks
    import sys
    import subprocess

    cmd = [sys.executable, "-u", update_smks.__file__]
    environ = os.environ.copy()
    environ["PYTHONUNBUFFERED"] = "1"

    if branch is not None:
        branch = get_branches().get(branch, branch)
        cmd += ['--branch', branch]

    if branch is not None:
        cmd += ['--repo_path', repo_path]

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return process
