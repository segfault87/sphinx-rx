# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

long_desc = '''
This is sphinx extension for documenting Rx schemas.

See more details at:

https://github.com/segfault87/sphinx-rx
'''


requires = ['Sphinx>=1.0']

setup(
    name='sphinx-rx',
    version='0.1.0',
    url='https://github.com/segfault87/sphinx-rx',
    download_url='http://pypi.python.org/pypi/sphinx-rx',
    license='BSD',
    author='Park Joon-Kyu',
    author_email='segfault87@gmail.com',
    description='Sphinx domain for HTTP APIs',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=['sphinxext'],
)
