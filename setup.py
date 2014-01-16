from distutils.core import setup

setup(name='openant',
      version='0.1',

      description='ANT and ANT-FS Python Library',
      long_description= open('README').read(),

      author='Gustav Tiger',
      author_email='gustav@tiger.name',

      url='http://www.github.com/Tigge/openant',

      classifiers=['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Healthcare Industry',
                   'License :: OSI Approved :: MIT License',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Software Development :: Libraries :: Python Modules'
                   ],

      packages=['ant', 'ant.base', 'ant.easy', 'ant.fs'],
      
      requires=['pyusb (>1.0a2)'],
      
      data_files=[('/etc/udev/rules.d', ['resources/ant-usb-sticks.rules'])]
      )

