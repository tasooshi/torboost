# -*- coding: utf-8 -*-
#######################################################################
# License: MIT License                                                #
# Homepage: https://github.com/tasooshi/torboost/                     #
# Version: 0.9.0                                                      #
#######################################################################

import setuptools


with open('README.md') as f:
    long_description = f.read()


setuptools.setup(
    name='torboost',
    version='0.9.0',
    author='tasooshi',
    author_email='tasooshi@pm.me',
    description='Download utility for Tor',
    license='MIT License',
    keywords=[
        'Tor',
        'onion',
        'download',
    ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tasooshi/torboost/',
    packages=setuptools.find_packages(),
    install_requires=(
        'requests[socks]==2.27.1',
        'stem==1.8.0',
    ),
    entry_points={
        'console_scripts': (
            'torboost=torboost.torboost:entry_point',
        ),
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ]
)
