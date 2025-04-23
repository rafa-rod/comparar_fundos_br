# -*- coding: utf-8 -*-
from setuptools import setup
import os, sys

PACKAGE = "comparar_fundos_br"

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

sys.path.append(os.path.join('src', PACKAGE))

import version

version_ = version.__version__

package_dir = \
{'': 'src'}

packages = \
[PACKAGE]

package_data = \
{'': ['*'],
 PACKAGE: ['media/*']}

install_requires = \
[
 'requests>=2.31,<3.0.0',
 'seaborn>=0.11.2,<0.12.0']

extras_require = \
{
 ':python_version >= "3.10"': ['matplotlib>=3.10.0', 'pandas>=2.2.3', 'numpy>=1.26.0', 'pyettj>=0.3.3', 'scipy>=1.11.0']}

setup_kwargs = {
    'name': 'comparar-fundos-br',
    'version': version_,
    'description': 'Download dados de fundos de investimento e realiza comparações.',
    'long_description_content_type': 'text/markdown',
    'long_description': long_description,
    'author': 'Rafael Rodrigues',
    'author_email': 'rafael.rafarod@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': f"https://github.com/rafa-rod/{PACKAGE}",
    'package_dir': package_dir,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'extras_require': extras_require,
    'python_requires': '>=3.10,<4.0',
}

setup(**setup_kwargs)