# Always prefer setuptools over distutils
from setuptools import setup

from os import path

here = path.abspath(path.dirname(__file__))
setup(name='py-lookingglass',
      version='1.01',
      py_modules=['lg'],
      url='https://github.com/andrew-azarov/py-lookingglass',
      download_url='https://github.com/ServerAstra/py-lookingglass/tarball/master',
      author='Andrew Azarov',
      license='MIT',
      author_email='andrew@serverastra.com',
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Environment :: Web Environment',
                   'Intended Audience :: Telecommunications Industry',
                   'Intended Audience :: System Administrators',
                   'Intended Audience :: Information Technology',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: POSIX',
                   'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
                   'Topic :: System :: Networking',
                   'Topic :: System :: Systems Administration'],
      description='Python looking glass WSGI implementation',
      install_requires=['paramiko>=1.15.1'],
      long_description="""py-lookingglass
===============

Python looking glass wsgi implementation

Requires:
---------

Python 2.6+

Standard python modules:

- telnetlib
- os
- socket
- cgi
- wsgi\_ref
- traceback
- random
- argparse
- json

External:

- paramiko

Setup:
------

To run out of the box just clone the repo or install using ``pip install py-lookingglass`` or ``easy_install py-lookingglass``, then:

``# python -m lg -h``

Or you can use it as WSGI callback

``lg.lookingglass(name="Looking Glass", cmds={'profile':{'command_name','actual command'}}, hosts=[('password','ip',int(port),int(connection_type),'name','profile')])``

Any additional hacks can be applied before init of class

Check ``help(lg.lookingglass)`` for more info

Should also install executable py-lookingglass
""",
      entry_points={
          'console_scripts': [
           'py-lookingglass = lg:main()',
          ],
      }
      )
