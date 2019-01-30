
.. meta::
    :description: Sphinx Extension autodoc_classinstance to document class instances.
    :keywords: Sphinx, Extension, class instance


***************************************
Sphinx Extension: autodoc_classinstance
***************************************

This is a Sphinx Extension to provide support for documenting class instances
(rather than class definitions themselves). Callable classes will look much
like functions but can also have properly documented methods and attributes.

With this extension you can document class instances with *autodoc* using
the "autoclassinstance" directive:

.. code-block:: rst

    .. autoclassinstance:: myinstance

        .. automethod:: mymethod

Class instances can also be documented manually with the "classinstance"
directive:

.. code-block:: rst

    .. classinstance:: myinstance(arg1, arg2)

        Docstring for myinstance.

        .. method:: mymethod(arg1)

            Docstring for a method.


Installation
============

1. Create an **_ext** folder in your document source directory.

2. Copy the **autodoc_classinstance.py** file into the **_ext** folder.

   Your folder directory structure could look like the following::

     └── source
         ├── _ext
         │   └── autodoc_classinstance.py
         ├── _static
         ├── _themes
         ├── conf.py
         ├── otherfolder
         └── otherfile.rst

3. Add the following lines to your **conf.py** file after the extensions list
   definition::

     # -- Configure custom extension: autodoc_classinstance --------------------
     if 'sphinx.ext.autodoc' in extensions:

         # Add custom extension directory ("_ext") to sys.path.
         dirname = os.path.abspath(os.path.dirname(globals().get('__file__', '.')))
         sys.path.insert(0, os.path.join(dirname, '_ext'))

         # Add to list of extensions (must appear after autodoc in list).
         extensions.append('autodoc_classinstance')

         # Suppress the warning given when the extension overrides the
         # registered "automethod" directive 
         suppress_warnings = [
             'app.add_directive',
         ]


..
    Layout based on:
    https://www.sphinx-doc.org/en/master/development/tutorials/helloworld.html
