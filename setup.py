from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='imapy',
      version='1.2.dev6',
      description='Imap for humans',
      long_description=readme(),
      keywords='imap library, email processing, imaplib',
      url='http://github.com/vladimarius/imapy',
      author='Vladimir Goncharov',
      author_email='vladimarius@gmail.com',
      license='MIT',
      packages=['imapy'],
      download_url='https://github.com/vladimarius/imapy',
      zip_safe=False,
      install_requires=[
          'beautifulsoup4',
          'IMAPClient',
          'six',
      ],
      classifiers=(
          'Intended Audience :: Developers',
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Topic :: Communications :: Email',
          'Topic :: Communications :: Email :: Post-Office :: IMAP',
          'Topic :: Software Development :: Libraries',
          'Topic :: Utilities'
      ),
)
