"""SysmonMQ setup.py."""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sysmonmq",
    version="0.0.1",
    author="Crowbar Z",
    author_email="crowbarz@outlook.com",
    description="Client for monitoring and controlling systems over MQTT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/crowbarz/sysmonmq.git",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Operating System :: POSIX :: Linux",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Networking :: Monitoring",
    ],
    python_requires=">=3.6",
    install_requires=[
        "inotify-simple==1.3.5",
        "paho-mqtt==1.5.1",
        "pyyaml==5.3.1",
        "python-slugify==4.0.1",
    ],
    entry_points={
        "console_scripts": [
            "sysmonmq=sysmonmq.sysmonmq:entry_point",
        ]
    },
)
