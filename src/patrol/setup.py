from setuptools import find_packages, setup

package_name = 'patrol'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Pasha',
    maintainer_email='205416082+Pavel-Bratchikov@users.noreply.github.com',
    description='Publish turtlesim motion commands with validated runtime parameters.',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={'console_scripts': ['patrol = patrol.patrol:main']},
)
