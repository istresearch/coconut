import setuptools
from coconut import __version__

with open("README.md", "r") as f:
    description = f.read()

with open("requirements.txt", "r") as f:
    requirements = [r.strip() for r in f.readlines() if len(r) > 0]


setuptools.setup(
    name=f"limesurvey-coconut",
    version=__version__,
    author="IST Research",
    author_email="support@istresearch.com",
    description="Coconut - A LimeSurvey data extraction and helper library",
    license="MIT License",
    long_description=description,
    long_description_content_type="text/markdown",
    url="https://github.com/istresearch/coconut",
    packages=["coconut"],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[requirements],
    include_package_data=True,
)
