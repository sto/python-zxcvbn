from distutils.core import setup
from babel.messages import frontend as babel

setup(name='zxcvbn',
      version='1.0.1',
      description='Password strength estimator',
      author='Ryan Pearl',
      author_email='rpearl@dropbox.com',
      url='https://www.github.com/rpearl/python-zxcvbn',
      packages=['zxcvbn'],
      package_data={'zxcvbn': ['generated/frequency_lists.json', 'generated/adjacency_graphs.json']},
      cmdclass = {'compile_catalog': babel.compile_catalog,
                  'extract_messages': babel.extract_messages,
                  'init_catalog': babel.init_catalog,
                  'update_catalog': babel.update_catalog}
     )
