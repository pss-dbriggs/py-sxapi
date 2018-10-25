from setuptools import setup, find_packages

setup(
	name='py_sxapi',
	version = '0.3',
	license = 'GPL-3.0',
	packages=find_packages(),
	#py_modules=['py_sxapi'],
	summary='A set of tools for using the SXAPIs with Python',
	author='David Briggs',
	author_email='david.briggs@psscompanies.com',
	url='https://bitbucket.org/psscorp/py-sxapi',
	include_package_data=True,
	install_requires=[
		'bs4','requests',
	],
)