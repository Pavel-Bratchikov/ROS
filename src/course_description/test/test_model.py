import math
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from course_description.model import expand_model


PACKAGE = Path(__file__).resolve().parents[1]
MODEL = Path(os.environ.get('PR06_MODEL', PACKAGE / 'urdf/vehicle.urdf.xacro'))
KIT = Path(os.environ.get('PR06_KIT', PACKAGE.parents[1] / '.course-kit/v1'))


@pytest.fixture(scope='module')
def robot():
    return ET.fromstring(expand_model(MODEL))


def xyz(text):
    return tuple(map(float, text.split()))


def transform(joint):
    origin = joint.find('origin')
    roll, pitch, yaw = xyz(origin.get('rpy', '0 0 0'))
    sr, sp, sy = map(math.sin, (roll, pitch, yaw))
    cr, cp, cy = map(math.cos, (roll, pitch, yaw))
    around_x = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    around_y = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    around_z = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return around_z @ around_y @ around_x, np.array(xyz(origin.get('xyz')))


def relative_to_base(robot, link):
    incoming = {joint.find('child').get('link'): joint for joint in robot.findall('joint')}
    rotation, position = np.eye(3), np.zeros(3)
    while link != 'base_link':
        joint = incoming[link]
        step_rotation, offset = transform(joint)
        rotation, position = step_rotation @ rotation, step_rotation @ position + offset
        link = joint.find('parent').get('link')
    return rotation, position


def test_one_connected_acyclic_tree(robot):
    links = [link.get('name') for link in robot.findall('link')]
    joints = robot.findall('joint')
    parents = {joint.find('child').get('link'): joint.find('parent').get('link') for joint in joints}
    assert len(links) == len(set(links)) == 12
    assert len(joints) == len(parents) == 11
    assert set(links) - parents.keys() == {'base_footprint'}
    for link in parents:
        visited = set()
        while link in parents:
            assert link not in visited
            visited.add(link)
            link = parents[link]
        assert link == 'base_footprint'
    assert not robot.findall('.//gazebo')
    assert not robot.findall('.//plugin')


def test_lidar_parent(robot):
    joint = robot.find("joint[@name='lidar_joint']")
    assert joint.get('type') == 'fixed'
    assert joint.find('child').get('link') == 'lidar_link'
    assert joint.find('parent').get('link') == 'base_link'


@pytest.mark.parametrize('sensor', ['camera_link', 'imu_link', 'lidar_link'])
def test_sensor_pose_in_base_frame(robot, sensor):
    rotation, position = relative_to_base(robot, sensor)
    np.testing.assert_allclose(position, [0.28, 0, 0.38])
    np.testing.assert_allclose(rotation, np.eye(3))


def test_camera_optical_axes(robot):
    rotation, _ = transform(robot.find("joint[@name='camera_optical_joint']"))
    expected = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]])
    np.testing.assert_allclose(rotation, expected, atol=1e-12)


def test_solid_links_have_separate_shapes_and_valid_inertia(robot):
    for link in robot.findall('link'):
        if link.get('name') in {'base_footprint', 'camera_optical_frame'}:
            continue
        assert link.find('visual/geometry') is not None
        assert link.find('collision/geometry') is not None
        assert float(link.find('inertial/mass').get('value')) > 0
        inertia = link.find('inertial/inertia').attrib
        tensor = [[float(inertia[f'i{min(a, b)}{max(a, b)}']) for b in 'xyz'] for a in 'xyz']
        moments = np.linalg.eigvalsh(tensor)
        assert np.isfinite(moments).all() and min(moments) > 0
        assert 2 * max(moments) <= sum(moments) + 1e-12


def test_finite_geometry_and_positive_sizes(robot):
    for node in robot.iter():
        for key, value in node.attrib.items():
            if key not in {'name', 'link', 'type'}:
                assert all(map(math.isfinite, xyz(value)))
        if node.tag in {'box', 'cylinder'}:
            assert all(value > 0 for text in node.attrib.values() for value in xyz(text))


@pytest.mark.parametrize(('base', 'track', 'radius'), [(0.8, 0.62, 0.12), (1.0, 0.70, 0.15)])
def test_dimension_overrides_move_axles_and_resize_wheels(base, track, radius):
    robot = ET.fromstring(expand_model(MODEL, wheelbase=base, track=track, wheel_radius=radius))
    for side, sign in (('left', 1), ('right', -1)):
        steering = robot.find(f"joint[@name='front_{side}_steering_joint']")
        assert steering.get('type') == 'revolute'
        assert xyz(steering.find('axis').get('xyz')) == (0, 0, 1)
        for axle, x in (('front', base / 2), ('rear', -base / 2)):
            name = f'{axle}_{side}_wheel'
            _, position = relative_to_base(robot, name)
            np.testing.assert_allclose(position, [x, sign * track / 2, 0])
            joint = robot.find(f"joint[@name='{name}_joint']")
            assert joint.get('type') == 'continuous'
            assert xyz(joint.find('axis').get('xyz')) == (0, 1, 0)
            for kind in ('visual', 'collision'):
                geometry = robot.find(f"link[@name='{name}']/{kind}/geometry/cylinder")
                assert float(geometry.get('radius')) == pytest.approx(radius)
    footprint_offset = robot.find("joint[@name='base_joint']/origin").get('xyz')
    assert xyz(footprint_offset) == pytest.approx((0, 0, radius))


@pytest.mark.parametrize('name', ['wheelbase', 'track', 'wheel_radius'])
@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf')])
def test_bad_dimensions_fail_validation(name, value):
    with pytest.raises(ValueError, match=name):
        expand_model(MODEL, **{name: value})


def test_base_and_wheels_match_course_sdf(robot):
    source = ET.parse(KIT / 'models/course_ackermann/model.sdf').getroot().find('model')
    for axle in ('front', 'rear'):
        for side in ('left', 'right'):
            name = f'{axle}_{side}_wheel'
            sdf_link = source.find(f"link[@name='{name}']")
            _, position = relative_to_base(robot, name)
            np.testing.assert_allclose(position, xyz(sdf_link.findtext('pose'))[:3])
            sdf_cylinder = sdf_link.find('collision/geometry/cylinder')
            urdf_cylinder = robot.find(f"link[@name='{name}']/collision/geometry/cylinder")
            for dimension in ('length', 'radius'):
                assert float(urdf_cylinder.get(dimension)) == float(sdf_cylinder.findtext(dimension))
    shape = 'link[@name="base_link"]/collision/geometry/box'
    assert xyz(robot.find(shape).get('size')) == xyz(source.find(shape).findtext('size'))


def test_check_urdf_accepts_expanded_model(tmp_path):
    output = tmp_path / 'vehicle.urdf'
    output.write_text(expand_model(MODEL), encoding='utf-8')
    result = subprocess.run(['check_urdf', str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
