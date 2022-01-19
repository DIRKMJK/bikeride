import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "readme.md").read_text()


setup(name='pybikeride',
    version='0.0.4',
    description='Analyse and plot gps files of bicycle rides',
    long_description=README,
    long_description_content_type="text/markdown",
    author='dirkmjk',
    author_email='info@dirkmjk.nl',
    url='https://github.com/DIRKMJK/bikeride',
    license="MIT",
    packages=['bikeride'],
    install_requires=[
        'python-dateutil', 'pandas', 'numpy', 'geopy',
        'fitparse', 'bs4', 'ipyleaflet'
    ],
    zip_safe=False)
