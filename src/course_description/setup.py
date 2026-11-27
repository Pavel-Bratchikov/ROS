from pathlib import Path

from setuptools import find_packages, setup


share = 'share/course_description'
resources = ('launch/description.launch.py', 'urdf/vehicle.urdf.xacro', 'rviz/vehicle.rviz')

setup(
    name='course_description',
    version='0.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/course_description']),
        (share, ['package.xml']),
        *((f'{share}/{Path(file).parent}', [file]) for file in resources),
    ],
    install_requires=['setuptools'],
    maintainer='Pasha',
    maintainer_email='205416082+Pavel-Bratchikov@users.noreply.github.com',
    description='Ackermann geometry, transforms and RViz configuration for PR06.',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
)
