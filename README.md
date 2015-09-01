py-lookingglass
===============

Python looking glass WSGI implementation

Requires:
---------
Python 2.6+

Standard python modules:
* telnetlib
* os
* socket
* cgi
* wsgi_ref
* random
* traceback
* argparse
* json

External:

* paramiko

Setup:
------
To run out of the box just clone the repo or install using `pip install py-lookingglass` or `easy_install py_lookingglass`, then:
```console
# python -m lg -h
```
Or you can use it as WSGI callback
```python
lg.lookingglass(name="Looking Glass", cmds=['command','list'], hosts=[('password','ip',port,'name')])
```
Any additional hacks can be applied before init of class

Check `help(lg.lookingglass)` for more info

Should also install executable py-lookingglass