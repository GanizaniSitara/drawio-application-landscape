import os


class ScriptConfig:

    EXPERIMENTAL = True

    # Where rendered .drawio files are written: the repository root by default.
    ROOT_FOLDER = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Open each rendered diagram in draw.io. Off by default; set the path below to
    # wherever draw.io is installed on your machine.
    OPEN_IN_DRAWIO = False
    DRAWIO_EXECUTABLE = r"C:\Program Files\draw.io\draw.io.exe"
