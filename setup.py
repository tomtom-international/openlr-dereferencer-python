from setuptools import setup

with open("README.md") as f:
    readme = f.read()

about = {}
with open("openlr_dereferencer/_version.py") as f:
    exec(f.read(), about)

setup(
    name=about["__title__"],
    version=about["__version__"],
    description=about["__description__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    license=about["__license__"],
    packages=[
        "openlr_dereferencer.example_sqlite_map",
        "openlr_dereferencer.maps",
        "openlr_dereferencer.maps.a_star",
        "openlr_dereferencer.decoding",
        "openlr_dereferencer.observer",
        "openlr_dereferencer",
        "openlr_dereferencer.stl_osm_map",
    ],
    install_requires=[
        "openlr==1.0.1",
        "geographiclib",
        "shapely",
        "stl_general @ git+ssh://git@github.com/StreetLight-Data/npp.git@develop#subdirectory=streetlight/stl_general",
    ],
    test_suite="tests",
    python_requires=">=3.6",
    classifiers=[
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
