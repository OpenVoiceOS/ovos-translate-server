#!/usr/bin/env python3
from setuptools import setup

setup(
    name='ovos-translate-server',
    version='0.0.1',
    description='simple flask server to host OpenVoiceOS translate plugins as a service',
    url='https://github.com/OpenVoiceOS/ovos-translate-server',
    author='JarbasAi',
    author_email='jarbasai@mailfence.com',
    license='Apache-2.0',
    packages=['ovos_translate_server'],
    install_requires=["ovos-plugin-manager>=0.0.5",
                      "flask"],
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Text Processing :: Linguistic',
        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='plugin lang detect translate OVOS OpenVoiceOS',
    entry_points={
        'console_scripts': [
            'ovos-translate-server=ovos_translate_server.__main__:main'
        ]
    }
)
