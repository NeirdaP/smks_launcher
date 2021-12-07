import fnmatch
import os

IMG_EXTS = ['.tiff', '.tif', '.exr', '.jpeg', '.jpg', '.png', '.tx']
VID_EXTS = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
AUD_EXTS = ['.mp3', '.wav', '.flac', '.aac']


REPLACE_IF_EXISTS = 1
UPDATE_IF_EXISTS = 2
RENAME_IF_EXISTS = 3
SKIP_IF_EXISTS = 4
ENV_VAR_MATCHER = None


def is_image(file):
    return any(file[-6:].lower().endswith(ext) for ext in IMG_EXTS)


def is_video(file):
    return any(file[-6:].lower().endswith(ext) for ext in VID_EXTS)


def is_audio(file):
    return any(file[-6:].lower().endswith(ext) for ext in AUD_EXTS)


def _void_progress_visitor(progress, message):
    pass


def _void_logger(message):
    pass


def url_to_path(url):
    try:
        import urllib.request as urllib
    except ImportError:
        import urllib
    return urllib.url2pathname(url.replace('file:', ''))


def file_creation_date(path):
    """
    http://stackoverflow.com/a/39501288/1709587
    """

    import os
    import platform

    if not os.path.exists(path):
        return 0
    if platform.system() == 'Windows':
        return os.path.getctime(path)
    else:
        stat = os.stat(path)
        try:
            return stat.st_birthtime  # Unix
        except AttributeError:
            return stat.st_ctime


def file_modification_date(path):
    """
    http://stackoverflow.com/a/39501288/1709587
    return time in seconds
    """

    import os
    import platform

    if not os.path.exists(path):
        return 0
    if platform.system() == 'Windows':
        return os.path.getmtime(path)
    else:
        stat = os.stat(path)
        return stat.st_mtime


def file_size(path):
    """
    http://stackoverflow.com/a/39501288/1709587
    return size in bytes
    """

    import os
    import platform

    if not os.path.exists(path):
        return 0
    if platform.system() == 'Windows':
        return os.path.getsize(path)
    else:
        stat = os.stat(path)
        return stat.st_size


def copy_file(source, destination_folder, destination_name='',
              if_exists_behavior=REPLACE_IF_EXISTS, logger=None, ensure_dir_exists=False, skip_pattern=None):
    """
    Copy a source file into a folder
    :param (str) source: Source path
    :param (str) destination_folder: Destination folder path
    :param (str) destination_name: Optional destination file name (otherwise it will take the source file name)
    :param (int) if_exists_behavior: REPLACE_IF_EXISTS, UPDATE_IF_EXISTS, RENAME_IF_EXISTS : Behavior if the folder already exists
    :param logger: Function that permit to treat messages
    :param ensure_dir_exists:
    :param (str) skip_pattern: fnmatch pattern which will skip file copy
    :return: Destination file
    """
    import shutil
    import os

    if logger is None:
        logger = _void_logger

    if not destination_name:
        destination_name = os.path.basename(source)

    destination = os.path.join(destination_folder, destination_name)
    do_it = False
    if os.path.exists(destination):
        if if_exists_behavior == REPLACE_IF_EXISTS:
            do_it = True
        elif if_exists_behavior == UPDATE_IF_EXISTS:
            if file_modification_date(source) - file_modification_date(destination) > 50:
                do_it = True
        elif if_exists_behavior == RENAME_IF_EXISTS:
            destination_name = "%d_" + destination_name
            i = 2
            while os.path.exists(os.path.join(destination_folder, destination_name % i)):
                i = i + 1
            do_it = True
    else:
        do_it = True

    if do_it:
        logger("Copying %s -> %s" % (os.path.abspath(source), os.path.abspath(destination)))
        if ensure_dir_exists:
            try:
                os.makedirs(destination_folder)
            except OSError:
                pass

        if not skip_pattern or not fnmatch.fnmatch(os.path.basename(source), skip_pattern):
            with open(destination, 'w'):
                pass
            shutil.copy2(source, destination)
    else:
        logger("Skipping Copy of %s -> %s" % (os.path.abspath(source), os.path.abspath(destination)))
    return destination


def copy_folder(source, destination_folder, destination_name=None, if_exists_behavior=REPLACE_IF_EXISTS,
                logger=None, skip_pattern=None):
    """
    Copy a source folder with all its files to a destination folder
    :param (str) source: Source folder path
    :param (str) destination_folder: Destination folder path
    :param (str) destination_name: Optional additional folder
    :param (int) if_exists_behavior: Behavior if the folder already exists
    :param logger: Logger
    :param skip_pattern: fnmatch pattern which will skip file copy
    :return: Destination folder
    """
    import shutil
    import os

    if logger is None:
        logger = _void_logger

    if destination_name is not None:
        destination_folder = os.path.join(destination_folder, destination_name)

    for root, dirs, files in os.walk(source):

        relative_dir = os.path.relpath(root, source)
        if relative_dir == '.':
            relative_dir = ''
            new_root = destination_folder
        else:
            new_root = os.path.join(destination_folder, relative_dir)

        # logger("Copying %s -> %s (%d files)" % (os.path.abspath(root), os.path.abspath(new_root), len(files))
        # logger("\tRoot: %s, Relative Dir: %s" % (os.path.abspath(root), relative_dir))
        do_it = False
        if if_exists_behavior != REPLACE_IF_EXISTS and os.path.exists(new_root):
            if if_exists_behavior == UPDATE_IF_EXISTS:
                if abs(file_modification_date(source) - file_modification_date(destination_folder)) > 50:
                    do_it = True
            elif if_exists_behavior == RENAME_IF_EXISTS:
                new_root_name = relative_dir + "_%d" if relative_dir else "%d"
                i = 2
                while os.path.exists(os.path.join(destination_folder, new_root_name % i)):
                    i = i + 1
                do_it = True
        else:
            try:
                os.makedirs(new_root)
            except OSError:
                pass
            do_it = True
        if do_it:
            for j, file in enumerate(files):
                if len(files) > 0:
                    logger("Copy %s \nprogress:%s" % (relative_dir, str(100*(j+1)/len(files))))
                copy_file(os.path.join(root, file), new_root, file, if_exists_behavior, None,
                          skip_pattern=skip_pattern)
            shutil.copystat(source, destination_folder)
    return destination_folder


def targeted_search_n_replace(path, replacements, result_buffer, progress_visitor=None):
    """
    Create new content by replacing file content according to the given replacements
    replacements should be a dict indexed with file positions for efficient search (if you don't have this information
    you can use a dict with only one key (0 for example)
    :param path: source file
    :param replacements: dict of (file position, iterable replacements (old, new))
    :param result_buffer: destination content, iterable list of new content texts (more efficient than a huge string)
    :param progress_visitor: optional callable visitor which will be called for sending the current state
    of the progress. Must accept two parameter (progression and message)
    """
    import re
    import codecs

    if progress_visitor is None:
        progress_visitor = _void_progress_visitor

    replacements_regex = dict()
    for position, replacements_set in replacements.items():
        replacements_regex[position] = [(re.compile(r'(?<!\w)%s(?!\w)' % re.escape(paths[0])), paths[1])
                                        for paths in replacements_set]

    replacements = sorted(replacements_regex.items(), key=lambda item: item[0])
    replace_iterator = iter(zip(replacements, replacements[1:] + [None]))
    current_replacement, next_replacement = next(replace_iterator)

    step = 1
    end = len(replacements)

    current_buffer = []
    process = False
    with codecs.open(path, "rb", "latin1") as fp:
        while 1:
            data = fp.read(1)
            if not data:
                break
            if not ord(data):
                raise RuntimeError("Cannot decode %s" % path)
            try:
                data.encode('ascii')  # from binary to text
                if ord(data) < 30 or ord(data) > 170:
                    raise UnicodeError(data)
            except UnicodeError:
                current_text = ''.join(current_buffer)
                current_buffer = []
                process = True
            else:
                if '\n' in data:
                    lines = data.split('\n', 1)
                    current_buffer.append(lines[0] + '\n')
                    current_text = ''.join(current_buffer)
                    current_buffer = [lines[1]]
                    process = True
                else:
                    current_buffer.append(data)
                data = ''
            if process:
                for pattern, new_path in current_replacement[1]:
                    current_text = pattern.sub(new_path, current_text)

                while next_replacement and fp.tell() >= next_replacement[0]:
                    try:
                        current_replacement, next_replacement = next(replace_iterator)
                        step += 1
                    except StopIteration:
                        break

                    message = '\n'.join('%s -> %s' % replacement for replacement in current_replacement[1])
                    progress_visitor((step * 100) / end,  "Current replacement:\n%s" % message)
                    for pattern, new_path in current_replacement[1]:
                        current_text = pattern.sub(new_path, current_text)

                result_buffer.append(current_text)
                process = False
            if data:
                result_buffer.append(data)

        if current_buffer:
            current_text = ''.join(current_buffer).strip()
            for pattern, new_path in current_replacement[1]:
                current_text = pattern.sub(new_path, current_text)
            for current_replacement, next_replacement in replace_iterator:
                for pattern, new_path in current_replacement[1]:
                    current_text = pattern.sub(new_path, current_text)
            result_buffer.append(current_text)


def find_frame_range(path):

    import os
    import re

    matcher = seq_matcher()

    first, last = -1, -1
    base = os.path.basename(path)
    if not path.endswith('mov') and not path.endswith('avi'):
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            return base, path, first, last
        match = matcher.search(path)
        if match:
            pattern = matcher.sub(r'.(\\d+).', base)
            base = base.split(match.group(), 1)[0]
            frame_finder = re.compile(pattern)

            for file in os.listdir(directory):
                match = frame_finder.match(file)
                if match:
                    frame = int(match.group(1))
                    if frame > last or last < 0:
                        last = frame
                    if frame < first or first < 0:
                        first = frame
    return base, path, first, last


SEQ_MATCHER = None


def seq_matcher():
    import re

    global SEQ_MATCHER
    if not SEQ_MATCHER:
        SEQ_MATCHER = re.compile(r'(\_|\.)(#+|%\dd|\d+)\.')
    return SEQ_MATCHER


def get_nuke_sequence_pattern(frame_path):
    matcher = seq_matcher()
    match = matcher.search(frame_path)
    if match:
        frame_str = match.group(2)
        return matcher.sub(r'%s%s.' % (match.group(1), '#' * len(frame_str)), frame_path)
    return frame_path


def get_sequence_pattern(frame_path):
    matcher = seq_matcher()
    match = matcher.search(frame_path)
    if match:
        frame_str = match.group(2)
        return matcher.sub(r'%s%s.' % (match.group(1), '%%0%dd' % len(frame_str)), frame_path)
    return frame_path


def get_sequence_glob_pattern(frame_path):
    matcher = seq_matcher()
    match = matcher.search(frame_path)
    if match:
        return matcher.sub(r'%s%s.' % (match.group(1), '*'), frame_path)
    return frame_path


def get_frame_id(frame_path):
    matcher = seq_matcher()
    match = matcher.search(frame_path)
    if match:
        return int(match.group(2))
    raise ValueError("Cannot find frame id")


def get_app_data_folder(subfolder=''):
    import platform

    system = platform.system().lower()
    if 'win' in system:
        folders = [os.environ['APPDATA'], os.environ['PROGRAMDATA'], os.environ['LOCALAPPDATA']]
    else:
        folders = ['/usr/share', os.path.expanduser('~/.config'),
                   os.path.expanduser('~'), os.path.expanduser('~/.local/share')]
    for f in folders:
        folder = os.path.join(f, subfolder)
        if os.path.exists(folder):
            return folder

    folder = os.path.join(folders[0], subfolder)
    try:
        os.makedirs(folder)
    except OSError:
        pass
    return folder


def open_file_manager(filepath):
    import subprocess
    import platform

    system = platform.system().lower()

    path = os.path.abspath(filepath)
    while path and not os.path.exists(path):
        path = os.path.dirname(path)
        if path == os.path.dirname(path):
            path = ''
            break

    if 'win' in system:
        if os.path.isfile(path):
            args = ["explorer", '/select,%s' % path]
        else:
            args = ["explorer", path]
        return subprocess.Popen(args)
    else:
        raise NotImplementedError("Not implemented for other OS")


def make_smart_path(path, environ=None, path_key_suffix="_PATH"):
    if environ is None:
        environ = os.environ
    path = path.replace('\\', '/')
    env_paths = []
    for key, value in environ.items():
        if key.endswith(path_key_suffix) and os.path.isdir(value):
            env_paths.append((key, value))

    for key, value in sorted(env_paths, key=lambda x: -len(x[1])):
        path = path.replace(value.replace('\\', '/') + '/', "$%s/" % key)
    return path


def compute_smart_path(path, environ=None):
    import re
    global ENV_VAR_MATCHER

    if environ is None:
        environ = os.environ

    if not ENV_VAR_MATCHER:
        ENV_VAR_MATCHER = re.compile(r'\$([\w\d]+)(\\|/)')
    for match in ENV_VAR_MATCHER.findall(path):
        var_name = match[0]
        if var_name in environ:
            path = path.replace('$%s' % var_name, environ[var_name])
    return path


def find_common_dirs(files, depth_lower_limit=3):
    """
    :param files:
    :param depth_lower_limit: find common dirs which depth is at least depth_limit
    (ex: depth_lower_limit=3, P:/KABARET_PROJECTS/TED will not be returned but
     P:/KABARET_PROJECTS/TED/banks will be)
    :return:
    """
    import os
    dirs = []

    for file in files:
        if len(file) > 1:
            dirs.append(os.path.dirname(file))

    roots = set()
    for dir in dirs:
        current_root = ''
        for dir2 in dirs:
            if dir2 == dir:
                continue
            dir2_parts = dir2.split('/')
            dir2_root = dir2_parts[0]
            for part in dir2_parts[1:]:
                if not dir.startswith(dir2_root):
                    break
                dir2_root += '/%s' % part
            if dir2_root.count('/') <= depth_lower_limit:
                continue
            dir2_root = dir2_root.rsplit('/', 1)[0]

            if len(dir2_root) > len(current_root):
                current_root = dir2_root
        roots.add(current_root or os.path.dirname(dir))
    roots = sorted(list(roots), key=lambda x: len(x))

    commons = []
    for root in roots:
        ok = True
        for existing in commons:
            if existing + '/' in root:
                ok = False
                break
        if ok:
            commons.append(root)
    return commons


def get_os_data_path(subfolder=''):
    """
    :return: data folder path given by the system
    """
    import os
    import tempfile

    data_paths = [os.environ.get("APPDATA"), os.environ.get("CommonProgramFiles(x86)"),
                   os.environ.get("CommonProgramFiles"), os.environ.get("ProgramData")]

    for path in data_paths:
        if os.path.isdir(path):
            return os.path.join(path, subfolder) if subfolder else path

    return os.path.join(tempfile.gettempdir(), subfolder) if subfolder else tempfile.gettempdir()