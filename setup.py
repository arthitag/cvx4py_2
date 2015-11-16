try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'name': 'cvx4py',
    'version': '0.1',
    'description': 'cvx like framework for python',
    'author': 'Arthita, Sayantan, Hui',
    'url': 'URL to get it at.',
    'download_url': 'https://github.com/ssarkar2/cvx4py',
    'author_email': 'supersarkar@gmail.com, arthitaghosh08@gmail.com, echodinghui@gmail.com',
    'version': '0.1',
    'packages': {'cvx4py'},
    'scripts': [],
    'zip_safe': False,
    'packages': [  'cvx4py',
                'cvx4py.ast',
                'cvx4py.ast.atoms',
                'cvx4py.ast.constraints',
                'cvx4py.ast.expressions',
                'cvx4py.ast.socps',
                'cvx4py.properties'],
}


#'install_requires': ['numpy', 'ply', 'scipy'],

setup(**config)