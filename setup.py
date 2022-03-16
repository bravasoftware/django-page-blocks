import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-page-blocks',
    version='0.2.0',
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='A simple, Wagtail CMS inspired content block engine for Django.  Intended to give slightly more control than regular flatpages.',
    long_description=README,
    long_description_content_type='text/markdown',
    url='https://www.bravasoftware.com/',
    author='Mark Skelton',
    author_email='mark@bravasoftware.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
