BRANCHES = dict(
    OFFICIAL="master",
    STABLE="9d0e49887a9e9cb84babad4ad789cda60bdd96d4",
    BETA="dev",
    default="master",
)


def get_branches():
    import json

    branches = BRANCHES.copy()
    with open('./branches.json') as fp:
        branches.update(json.load(fp))

    return branches


def update_smks_studio(branch=None, repo_path=None):
    import update_smks
    import sys
    import subprocess

    cmd = [sys.executable, update_smks.__file__]

    if branch is not None:
        branch = get_branches().get(branch, branch)
        cmd += ['--branch', branch]

    if branch is not None:
        cmd += ['--repo_path', repo_path]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return process
