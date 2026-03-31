pingtop
=======

Modern multi-host ping monitor with a Textual TUI.

Features
--------

- Monitor multiple hosts concurrently in a live Textual table
- Keep BSD-style ping summary output on exit
- Add, edit, delete, pause, and reset hosts during a session
- Export final statistics as JSON or CSV
- Keep a raw ICMP engine instead of shelling out to the system ``ping`` command

Requirements
------------

- Python 3.10+
- Poetry 2.x

Install
-------

::

   poetry install

Run
---

::

   poetry run pingtop 1.1.1.1 8.8.8.8

CIDR notation is also supported and expands to the usable hosts in that subnet:

::

   poetry run pingtop 10.22.76.19/24

You can also load hosts from a file:

::

   poetry run pingtop --hosts-file hosts.txt

Useful options:

::

   poetry run pingtop --help

   Usage: pingtop [OPTIONS] [HOSTS]...

Options include:

- ``-i, --interval`` ping interval in seconds
- ``-t, --timeout`` timeout in seconds
- ``-s, --packet-size`` ICMP payload size in bytes
- ``--hosts-file`` newline-delimited host list
- ``--summary / --no-summary`` print BSD-style summary on exit
- ``--export`` output path
- ``--export-format [json|csv]`` export format override
- ``--log-file`` log destination
- ``--log-level`` log verbosity

Key bindings
------------

- ``a`` add host
- ``e`` edit selected host
- ``d`` delete selected host
- ``space`` pause or resume selected host
- ``p`` pause or resume all hosts
- ``r`` reset selected host statistics
- ``R`` reset all host statistics
- ``s`` cycle sort key
- ``S`` reverse sort order
- ``enter`` focus details
- ``tab`` switch focus
- ``q`` quit

Permissions
-----------

``pingtop`` uses ICMP sockets directly. On Linux, non-root access depends on
``net.ipv4.ping_group_range``. If you see permission errors, inspect the value:

::

   cat /proc/sys/net/ipv4/ping_group_range

Then widen the allowed range so your user or group can open ICMP sockets:

::

   sudo sysctl -w net.ipv4.ping_group_range='0 1001'

Development
-----------

::

   poetry run pytest
   poetry run ruff check .
   poetry run mypy src

Credits
-------

- The raw ICMP implementation is derived from the original ``pingtop`` project.
- The TUI is now built with `Textual <https://textual.textualize.io/>`__.
