from setuptools import setup, find_packages

setup(
    name='girder_interactive_thumbnails',
    version='1.0.0',
    description='Use VTK python to generate a series of thumbnails of a dataset.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache 2.0',
    classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Environment :: Web Environment',
      'License :: OSI Approved :: Apache Software License'
    ],
    include_package_data=True,
    packages=find_packages(exclude=['plugin_tests']),
    zip_safe=False,
    install_requires=['girder>=3.0.0a1', 'girder-worker', 'girder-worker-utils'],
    entry_points={
        'girder.plugin': [
            'interactive_thumbnails = girder_interactive_thumbnails:InteractiveThumbnailsPlugin'
        ]
    }
)
