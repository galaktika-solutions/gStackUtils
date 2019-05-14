===========
gstackutils
===========

``gstackutils`` is a collection of utilities used in ``gstack`` based projects.
The following ``gstack`` related tasks are handled by the package:

.. toctree::

  config
  dbsetup
  backup
  run
  helpers


Basic Usage
===========

Create a ``gstack_conf.py`` file somewhere in your project.
When



.. Command Line Interface
.. ======================
..
.. ``cert``
.. ........
..
.. .. code-block:: text
..
..   Usage: gstack cert [OPTIONS]
..
..     Generates certificates for development purposes.
..
..   Options:
..     -n, --name TEXT  Name the generated certificate is valid for.
..     -i, --ip TEXT    IP address the generated certificate is valid for.
..     --help           Show this message and exit.
..
..
..
.. ---
.. API
.. ---
..
.. .. autofunction:: gstackutils.cert.createcerts
