from glob import glob

from setuptools import find_packages, setup

package_name = 'turtle_bringup'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Pasha',
    maintainer_email='205416082+Pavel-Bratchikov@users.noreply.github.com',
    description='Launch a turtlesim simulator from a ROS 2 workspace.',
    license='Apache-2.0',
)
