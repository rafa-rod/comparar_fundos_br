# -*- coding: utf-8 -*-
from setuptools import setup
import subprocess
from os import path

this_directory = path.abspath(path.dirname(__file__))

with open(path.join(this_directory, 'README_pypi.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(this_directory, 'comparar_fundos_br', 'version.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('"')[1]

packages = \
['comparar_fundos_br']

package_data = \
{'': ['*']}

install_requires = \
['DateTime>=4.5,<5.0',
 'bar-chart-race>=0.1.0,<0.2.0',
 'requests>=2.28.1,<3.0.0',
 'seaborn>=0.11.2,<0.12.0',
 'yfinance>=0.1.74,<0.2.0']

extras_require = \
{':python_version <= "3.9"': ['matplotlib<=3.7.1', 'pandas<=1.5.3', 'numpy<1.26.0', 'pyettj<=0.3.2', 'scipy>=1,7,<1.9.1'],
 ':python_version >= "3.10"': ['matplotlib>=3.10.0', 'pandas>=2.2.3', 'numpy>=1.26.0', 'pyettj>=0.3.3', 'scipy>=1.13.1']}

setup_kwargs = {
    'name': 'comparar-fundos-br',
    'version': version,
    'description': 'Download dados de fundos de investimento e realiza comparações.',
    'long_description': long_description,
    'long_description_content_type': "text/markdown",
    'author': 'Rafael Rodrigues',
    'author_email': 'rafael.rafarod@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': "",
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.8.5,<4.0',
}


setup(**setup_kwargs)