# -*- coding: utf-8 -*-
######################################################
#     _____                  _____      _     _      #
#    (____ \       _        |  ___)    (_)   | |     #
#     _   \ \ ____| |_  ____| | ___ ___ _  _ | |     #
#    | |  | )/ _  |  _)/ _  | |(_  / __) |/ || |     #
#    | |__/ ( ( | | | ( ( | | |__| | | | ( (_| |     #
#    |_____/ \_||_|___)\_||_|_____/|_| |_|\____|     #
#                                                    #
#    Copyright (c) 2022 Kangas Development Team      #
#    All rights reserved                             #
######################################################

import subprocess
import sys
import time
import urllib
import webbrowser

import psutil

from ._version import __version__  # noqa
from .datatypes import Audio, Curve, DataGrid, Image, Text, Video  # noqa
from .utils import _in_colab_environment, _in_jupyter_environment, get_localhost

KANGAS_BACKEND_PROXY = None


def _is_running(name, command):
    for pid in psutil.pids():
        try:
            process = psutil.Process(pid)
        except Exception:
            continue
        if process.name().startswith(name) and command in " ".join(process.cmdline()):
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    return False


def _process_method(name, command, method):
    for pid in psutil.pids():
        try:
            process = psutil.Process(pid)
        except Exception:
            continue
        if process.name().startswith(name) and command in " ".join(process.cmdline()):
            return getattr(process, method)()


def terminate():
    """
    Terminate the Kangas servers.

    Note: this should never be needed.

    ```python
    >>> import kangas
    >>> kangas.terminate()
    ```
    """
    _process_method("node", "kangas", "terminate")
    _process_method("kangas", "server", "terminate")


def launch(host=None, port=4000, debug=False):
    """
    Launch the Kangas servers.

    Note: this should never be needed as the Kangas
          servers are started automatically when needed.

    Args:
        host: (str) the name or IP of the machine the
            servers should listen on.
        port: (int) the port of the Kangas frontend server. The
            backend server will start on port + 1.
        debug: (bool) if True, debugging output will be
            shown as you run the servers.

    Example:

    ```python
    >>> import kangas
    >>> kangas.launch()
    ```
    """
    global KANGAS_BACKEND_PROXY

    host = host if host is not None else get_localhost()

    if not _is_running("node", "kangas"):
        terminate()
        if _in_colab_environment():
            from google.colab import output

            KANGAS_BACKEND_PROXY = output.eval_js(
                "(async () => {return await google.colab.kernel.proxyPort(%s)})()"
                % str(port + 1)
            )

        subprocess.Popen(
            (
                [
                    sys.executable,
                    "-m",
                    "kangas.cli.server",
                    "--frontend-port",
                    str(port),
                    "--backend-port",
                    str(port + 1),
                    "--open",
                    "no",
                ]
                + (["--host", host] if host is not None else [])
                + (
                    ["--backend-proxy", KANGAS_BACKEND_PROXY]
                    if KANGAS_BACKEND_PROXY is not None
                    else []
                )
                + (["--debug"] if debug else [])
            )
        )
        time.sleep(2)

    return "http://%s:%s/" % (host, port)


def show(
    datagrid=None, host=None, port=4000, debug=False, height="750px", width="100%"
):
    """
    Start the Kangas servers and show the DatGrid UI
    in an IFrame or browser.

    Args:
        datagrid: (str) the DataGrid's location from current
            directory
        host: (str) the name or IP of the machine the
            servers should listen on.
        port: (int) the port of the Kangas frontend server. The
            backend server will start on port + 1.
        debug: (bool) if True, debugging output will be
            shown as you run the servers.
        height: (str) the height (in "px" pixels) of the
            iframe shown in the Jupyter notebook.
        width: (str) the width (in "px" pixels or "%" percentages) of the
            iframe shown in the Jupyter notebook.

    Example:

    ```python
    >>> import kangas
    >>> kangas.show("./example.datagrid")
    ```
    """
    from IPython.display import IFrame, Javascript, display

    url = launch(host, port, debug)

    if datagrid:
        query_vars = {"datagrid": datagrid}
        qvs = "?" + urllib.parse.urlencode(query_vars)
        url = "%s%s" % (url, qvs)
    else:
        qvs = ""

    if _in_colab_environment():
        display(
            Javascript(
                """
(async ()=>{{
    fm = document.createElement('iframe');
    fm.src = (await google.colab.kernel.proxyPort({port})) + '{qvs}';
    fm.width = '{width}';
    fm.height = '{height}';
    fm.frameBorder = 0;
    document.body.append(fm);
}})();
""".format(
                    port=port, width=width, height=height, qvs=qvs
                )
            )
        )

    elif _in_jupyter_environment():
        display(IFrame(src=url, width=width, height=height))

    else:
        webbrowser.open(url, autoraise=True)


def read_dataframe(dataframe, **kwargs):
    """
    Takes a columnar pandas dataframe and returns a DataGrid.

    Args:
        dataframe: (pandas.DataFrame) the DataFrame to read from.
            Only works on in-memory DataFrames. If your DataFrame is
            stored on disk, you will need to load it first.
        datetime_format: (str) the Python date format that dates
            are read. For example, use "%Y/%m/%d" for dates like
            "2022/12/01".
        heuristics: (bool) whether to guess that some float values are
            datetime representations
        name: (str) the name to use for the DataGrid
        filename: (str) the filename to save the DataGrid to
        converters: (dict) dictionary of functions where the key
            is the columns name, and the value is a function that
            takes a value and converts it to the proper type and
            form.

    Note: the file or URL may end with ".zip", ".tgz", ".gz", or ".tar"
        extension. If so, it will be downloaded and unarchived. The JSON
        file is assumed to be in the archive with the same name as the
        file/URL. If it is not, then please use the kangas.download()
        function to download, and then read from the downloaded file.

    Examples:

    ```python
    >>> import kangas
    >>> from pandas import DataFrame
    >>> df = DataFrame(...)
    >>> dg = kangas.read_dataframe(df)
    >>> dg.save()
    ```
    """
    return DataGrid.read_dataframe(dataframe, **kwargs)


def read_datagrid(filename, **kwargs):
    """
    Reads a DataGrid from a filename. Returns
    the DataGrid.

    Args:
        filename: the name of the file or URL to read the DataGrid
            from

    Note: the file or URL may end with ".zip", ".tgz", ".gz", or ".tar"
        extension. If so, it will be downloaded and unarchived. The JSON
        file is assumed to be in the archive with the same name as the
        file/URL. If it is not, then please use the kangas.download()
        function to download, and then read from the downloaded file.

    Examples:

    ```python
    >>> import kangas
    >>> dg = kangas.read_datagrid("example.datagrid")
    >>> dg = kangas.read_datagrid("http://example.com/example.datagrid")
    >>> dg = kangas.read_datagrid("http://example.com/example.datagrid.zip")
    >>> dg.save()
    ```
    """
    return DataGrid.read_datagrid(filename, **kwargs)


def read_json(filename, **kwargs):
    """
    Reads JSON Lines from a filename. Returns
    the DataGrid.

    Args:
        filename: the name of the file or URL to read the DataGrid from
        datetime_format: (str) the Python date format that dates
            are read. For example, use "%Y/%m/%d" for dates like
            "2022/12/01".
        heuristics: (bool) whether to guess that some float values are
            datetime representations
        name: (str) the name to use for the DataGrid
        converters: (dict) dictionary of functions where the key
            is the columns name, and the value is a function that
            takes a value and converts it to the proper type and
            form.

    Note: the file or URL may end with ".zip", ".tgz", ".gz", or ".tar"
        extension. If so, it will be downloaded and unarchived. The JSON
        file is assumed to be in the archive with the same name as the
        file/URL. If it is not, then please use the kangas.download()
        function to download, and then read from the downloaded file.

    Examples:

    ```python
    >>> import kangas
    >>> dg = kangas.read_json("data.json")
    >>> dg = kangas.read_json("https://data.json.zip")
    >>> dg = kangas.read_json("https://data.json.gz")
    >>> dg.save()
    ```
    """
    return DataGrid.read_json(filename, **kwargs)


def download(url, ext=None):
    """
    Downloads a file, and unzips, untars, or ungzips it.

    Args:
        url: (str) the URL of the file to download
        ext: (optional, str) the format of the archive: "zip",
            "tgz", "gz", or "tar".

    Note: the URL may end with ".zip", ".tgz", ".gz", or ".tar"
        extension. If so, it will be downloaded and unarchived.
        If the URL doesn't have an extension or it does not match
        one of those, but it is one of those, you can override
        it using the `ext` argument.

    Example:

    ```python
    >>> import kangas
    >>> kangas.download("https://example.com/example.images.zip")
    ```
    """
    return DataGrid.download(url, ext)


def read_csv(
    filename,
    header=0,
    sep=",",
    quotechar='"',
    heuristics=True,
    datetime_format=None,
    converters=None,
):
    """
    Takes a CSV filename and returns a DataGrid.

    Args:
        filename: the CSV file or URL to import
        header: if True, use the first row as column headings
        sep:  used in the CSV parsing
        quotechar: used in the CSV parsing
        heuristics: if True, guess that some numbers might be dates
        datetime_format: (str) the Python date format that dates
            are read. For example, use "%Y/%m/%d" for dates like
            "2022/12/01".
        converters: (dict, optional) A dictionary of functions for converting
            values in certain columns. Keys are column labels.

    Note: the file or URL may end with ".zip", ".tgz", ".gz", or ".tar"
        extension. If so, it will be downloaded and unarchived. The JSON
        file is assumed to be in the archive with the same name as the
        file/URL. If it is not, then please use the kangas.download()
        function to download, and then read from the downloaded file.

    Examples:

    ```python
    >>> import kangas
    >>> dg = kangas.read_csv("example.csv")
    >>> dg = kangas.read_csv("http://example.com/example.csv")
    >>> dg = kangas.read_csv("http://example.com/example.csv.zip")
    >>> dg.save()
    ```
    """
    return DataGrid.read_csv(
        filename, header, sep, quotechar, heuristics, datetime_format, converters
    )
