===========
gstackutils
===========


.. toctree::

   config


----------------------
Command Line Interface
----------------------

``cert``
........

.. code-block:: text

  Usage: gstack cert [OPTIONS]

    Generates certificates for development purposes.

  Options:
    -n, --name TEXT  Name the generated certificate is valid for.
    -i, --ip TEXT    IP address the generated certificate is valid for.
    --help           Show this message and exit.



---
API
---

.. autofunction:: gstackutils.createcerts
