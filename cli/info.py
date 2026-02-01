"""
CLI command: Get robot information.

Displays:
- Basic info: version and serial number
- Battery level
- Chassis: position, attitude, velocity, status
- Robotic arm position (EP Engineering Robot)
- Gripper status (EP Engineering Robot)
- Servo data (if available)
- Distance sensor readings (front, right, back, left)

Use --wait to increase sensor data collection time for more accurate readings.
"""

import click
import time
import threading
from .connection import connect_robot


# Storage for subscription data
_data = {}
_data_lock = threading.Lock()


def _make_callback(key):
    """Factory to create callbacks that store data."""
    def callback(*args):
        with _data_lock:
            _data[key] = args if len(args) > 1 else args[0]
    return callback


@click.command()
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
@click.option('--wait', '-w', default=1.5, help='Seconds to wait for sensor data')
def info(local_ip, robot_ip, wait):
    """
    Get information about the connected robot.
    
    \b
    Displays:
      - Version and serial number
      - Battery level
      - Chassis position, attitude, velocity, status
      - Robotic arm position (EP Engineering Robot)
      - Gripper status (EP Engineering Robot)
      - Distance sensor readings (front, right, back, left)
    
    \b
    Examples:
      robomaster info          # Basic info (1.5s)
      robomaster info -w 3     # Wait 3s for more data
    """
    
    # Reset data
    global _data
    _data = {}
    
    with connect_robot(local_ip, robot_ip) as ep_robot:
        click.echo("")
        
        # === Basic Info ===
        click.echo("━━━ Basic Info ━━━")
        try:
            version = ep_robot.get_version()
            click.echo(f"📋 Version: {version}")
        except Exception as e:
            click.echo(f"❌ Version: {e}")
        
        try:
            sn = ep_robot.get_sn()
            click.echo(f"🔢 Serial: {sn}")
        except Exception as e:
            click.echo(f"ℹ️  Serial: {e}")
        
        # === Subscribe to sensor data ===
        click.echo(f"\n📡 Collecting sensor data ({wait}s)...")
        
        # Battery
        try:
            ep_robot.battery.sub_battery_info(freq=10, callback=_make_callback('battery'))
        except Exception as e:
            click.echo(f"  ⚠️  Battery: {e}")
        
        # Chassis
        try:
            chassis = ep_robot.chassis
            chassis.sub_position(freq=10, callback=_make_callback('position'))
            chassis.sub_attitude(freq=10, callback=_make_callback('attitude'))
            chassis.sub_status(freq=10, callback=_make_callback('status'))
            chassis.sub_velocity(freq=10, callback=_make_callback('velocity'))
        except Exception as e:
            click.echo(f"  ⚠️  Chassis: {e}")
        
        # Robotic Arm (if available)
        try:
            arm = ep_robot.robotic_arm
            arm.sub_position(freq=10, callback=_make_callback('arm'))
        except Exception as e:
            pass  # Arm may not be available
        
        # Gripper (if available)
        try:
            gripper = ep_robot.gripper
            gripper.sub_status(freq=10, callback=_make_callback('gripper'))
        except Exception as e:
            pass  # Gripper may not be available
        
        # Servo
        try:
            servo = ep_robot.servo
            servo.sub_servo_info(freq=10, callback=_make_callback('servo'))
        except Exception as e:
            pass  # Servo may not be available
        
        # Distance Sensor (if available)
        try:
            sensor = ep_robot.sensor
            sensor.sub_distance(freq=10, callback=_make_callback('distance'))
        except Exception as e:
            pass  # Sensor may not be available
        
        # Wait for data
        time.sleep(wait)
        
        # === Display Results ===
        with _data_lock:
            # Battery
            click.echo("\n━━━ Battery ━━━")
            if 'battery' in _data:
                click.echo(f"🔋 Level: {_data['battery']}%")
            else:
                click.echo("🔋 Level: (no data)")
            
            # Chassis
            click.echo("\n━━━ Chassis ━━━")
            if 'position' in _data:
                pos = _data['position']
                if isinstance(pos, tuple) and len(pos) >= 3:
                    click.echo(f"📍 Position: x={pos[0]:.3f}m, y={pos[1]:.3f}m, yaw={pos[2]:.1f}°")
                else:
                    click.echo(f"📍 Position: {pos}")
            else:
                click.echo("📍 Position: (no data)")
            
            if 'attitude' in _data:
                att = _data['attitude']
                if isinstance(att, tuple) and len(att) >= 3:
                    click.echo(f"🔄 Attitude: yaw={att[0]:.1f}°, pitch={att[1]:.1f}°, roll={att[2]:.1f}°")
                else:
                    click.echo(f"🔄 Attitude: {att}")
            
            if 'velocity' in _data:
                vel = _data['velocity']
                if len(vel) >= 3:
                    click.echo(f"💨 Velocity: vx={vel[0]:.2f}, vy={vel[1]:.2f}, vz={vel[2]:.2f}")
                if len(vel) >= 6:
                    click.echo(f"⚙️  Wheels: w1={vel[3]}, w2={vel[4]}, w3={vel[5]}")
                if len(vel) >= 7:
                    click.echo(f"        w4={vel[6]}")
            
            if 'status' in _data:
                status = _data['status']
                # Status is a tuple of booleans
                labels = ['static', 'uphill', 'downhill', 'on_slope', 
                         'pick_up', 'slip', 'impact', 'hill_static', 'hill_err']
                active = [l for l, v in zip(labels, status) if v]
                click.echo(f"📊 Status: {', '.join(active) if active else 'normal'}")
            
            # Robotic Arm
            if 'arm' in _data:
                click.echo("\n━━━ Robotic Arm ━━━")
                arm = _data['arm']
                if isinstance(arm, tuple) and len(arm) >= 2:
                    click.echo(f"🦾 Position: x={arm[0]:.1f}mm, y={arm[1]:.1f}mm")
                else:
                    click.echo(f"🦾 Data: {arm}")
            
            # Gripper
            if 'gripper' in _data:
                click.echo("\n━━━ Gripper ━━━")
                click.echo(f"✊ Status: {_data['gripper']}")
            
            # Servo
            if 'servo' in _data:
                click.echo("\n━━━ Servos ━━━")
                click.echo(f"🔧 Data: {_data['servo']}")
            
            # Distance Sensor
            if 'distance' in _data:
                click.echo("\n━━━ Distance Sensor ━━━")
                dist = _data['distance']
                if isinstance(dist, (tuple, list)) and len(dist) >= 4:
                    click.echo(f"📏 Front: {dist[0]} mm")
                    click.echo(f"📏 Right: {dist[1]} mm")
                    click.echo(f"📏 Back:  {dist[2]} mm")
                    click.echo(f"📏 Left:  {dist[3]} mm")
                else:
                    click.echo(f"📏 Distance: {dist}")
        
        # Unsubscribe
        try:
            ep_robot.battery.unsub_battery_info()
            ep_robot.chassis.unsub_position()
            ep_robot.chassis.unsub_attitude()
            ep_robot.chassis.unsub_status()
            ep_robot.chassis.unsub_velocity()
        except:
            pass
        
        try:
            ep_robot.robotic_arm.unsub_position()
        except:
            pass
        
        try:
            ep_robot.gripper.unsub_status()
        except:
            pass
        
        try:
            ep_robot.servo.unsub_servo_info()
        except:
            pass
        
        try:
            ep_robot.sensor.unsub_distance()
        except:
            pass
        
        click.echo("")


if __name__ == '__main__':
    info()
