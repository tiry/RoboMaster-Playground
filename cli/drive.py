"""
CLI command: Drive the robot with a USB joystick while viewing video feed.

Designed for EP Engineering Robot (arm + gripper).

Controls:
- Left stick: Forward/backward and strafe left/right  
- Right stick X: Rotate left/right
- D-pad up/down: Arm Y position (up/down)
- D-pad left/right: Arm X position (retract/extend)
- Y button: Arm recenter
- X button: Toggle LED feedback on/off
- Bumpers: Gripper open (RB) / close (LB)
- A button: Speed boost

LED feedback (on by default):
- OFF when not moving
- CYAN when moving
- RED when moving with boost (A button)

Includes simulation mode (--simu) to test controls without robot connection.
Use --record to save commands to a JSON file for later replay.
"""

import click
import cv2
import pygame

from .joystick import Joystick
from .config import MOVEMENT, ARM
from .recorder import CommandRecorder, CommandPlayer
from driver import RobotDriver, SDKDriver, RecordingDriver, run_simulation


def drive_loop(joystick: Joystick, driver: RobotDriver, mode: str, show_video: bool,
               recorder: CommandRecorder = None):
    """Main drive loop using abstract driver interface.
    
    Args:
        joystick: Joystick instance
        driver: Robot driver
        mode: 'continuous' or 'step'
        show_video: Whether to show video
        recorder: Optional CommandRecorder for recording mode
    """
    
    click.echo(f"\n🚗 Ready to drive! Mode: {mode}")
    click.echo("   Left stick: Move | Right stick X: Rotate")
    click.echo("   D-pad up/down: Arm Y | D-pad left/right: Arm X")
    click.echo("   Y button: Arm recenter | X button: Toggle LED feedback")
    click.echo("   LB: Close gripper | RB: Open gripper | A: Speed boost")
    if recorder:
        click.echo("   B button: Stop recording")
    click.echo("   Press 'q' or ESC to quit\n")
    
    # LED feedback state
    prev_x_button = False
    led_feedback_enabled = True  # Dynamic LED feedback on by default
    last_led_state = None  # Track: None=off, 'cyan'=moving, 'red'=boost
    
    try:
        while True:
            state = joystick.get_state()
            
            # Speed multiplier (A button for boost)
            speed_mult = MOVEMENT.get('boost_multiplier', 2.0) if state.a else 1.0
            
            # Chassis control
            if mode == 'continuous':
                # Calculate analog intensity (0-1) based on stick displacement
                left_intensity = max(abs(state.left_x), abs(state.left_y))
                right_intensity = abs(state.right_x)
                
                # Apply analog intensity as multiplier (more push = more speed)
                # Combined with boost button for cumulative effect
                xy_mult = left_intensity * speed_mult
                z_mult = right_intensity * speed_mult
                
                vx = state.left_y * MOVEMENT['continuous_speed_xy'] * xy_mult
                vy = state.left_x * MOVEMENT['continuous_speed_xy'] * xy_mult
                # For rotation: use sign for direction, intensity already in z_mult
                # Stick right (positive) = rotate right (positive vz in SDK)
                rotation_sign = 1 if state.right_x > 0 else (-1 if state.right_x < 0 else 0)
                vz = rotation_sign * MOVEMENT['continuous_speed_z'] * z_mult
                
                if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(vz) > 0.01:
                    driver.drive_speed(vx, vy, vz)
            
            elif mode == 'step':
                # Only send step command if chassis is ready (previous move completed)
                if driver.is_chassis_ready():
                    if abs(state.left_y) > 0.5 or abs(state.left_x) > 0.5 or abs(state.right_x) > 0.5:
                        x = MOVEMENT['step_forward'] if state.left_y > 0.5 else (-MOVEMENT['step_forward'] if state.left_y < -0.5 else 0)
                        y = MOVEMENT['step_strafe'] if state.left_x > 0.5 else (-MOVEMENT['step_strafe'] if state.left_x < -0.5 else 0)
                        # Invert rotation: stick right = positive z = rotate left in SDK, so negate
                        z = -MOVEMENT['step_rotate'] if state.right_x > 0.5 else (MOVEMENT['step_rotate'] if state.right_x < -0.5 else 0)
                        
                        if x != 0 or y != 0 or z != 0:
                            driver.drive_move(x, y, z, MOVEMENT['speed_xy'], MOVEMENT['speed_z'])
            
            # Arm control (D-pad + Y button)
            if driver.is_arm_ready():
                # Y button: recenter arm
                if state.y:
                    driver.arm_recenter()
                else:
                    # D-pad: move arm
                    y_delta = 0
                    if state.dpad_up:
                        y_delta = ARM['step_y']
                    elif state.dpad_down:
                        y_delta = -ARM['step_y']
                    
                    x_delta = 0
                    if state.dpad_right:
                        x_delta = ARM['step_x']
                    elif state.dpad_left:
                        x_delta = -ARM['step_x']
                    
                    if x_delta != 0 or y_delta != 0:
                        driver.arm_move(x_delta, y_delta)
            
            # Gripper control - progressive open/close while button held
            if state.lb:
                driver.gripper_close(power=50)  # Continuously closes while held
            elif state.rb:
                driver.gripper_open(power=50)   # Continuously opens while held
            else:
                driver.gripper_stop()           # Stop when no button pressed
            
            # LED feedback toggle (X button - edge triggered)
            if state.x and not prev_x_button:
                led_feedback_enabled = not led_feedback_enabled
                if not led_feedback_enabled:
                    driver.led_off()
                    last_led_state = None
                click.echo(f"💡 LED feedback {'ON' if led_feedback_enabled else 'OFF'}")
            prev_x_button = state.x
            
            # Dynamic LED feedback based on movement
            if led_feedback_enabled:
                # Detect if moving (any significant stick input)
                is_moving = (abs(state.left_x) > 0.2 or abs(state.left_y) > 0.2 or 
                            abs(state.right_x) > 0.2)
                is_boost = state.a and is_moving
                
                # Determine target LED state
                if is_boost:
                    target_led = 'red'
                elif is_moving:
                    target_led = 'cyan'
                else:
                    target_led = None  # off
                
                # Only update if state changed
                if target_led != last_led_state:
                    if target_led == 'red':
                        driver.led_on(255, 0, 0)
                    elif target_led == 'cyan':
                        driver.led_on(0, 255, 255)
                    else:
                        driver.led_off()
                    last_led_state = target_led
            
            # Video display
            if show_video:
                img = driver.get_video_frame()
                if img is not None:
                    cv2.putText(img, f"L: ({state.left_x:.1f}, {state.left_y:.1f})", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(img, f"R: ({state.right_x:.1f}, {state.right_y:.1f})", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    speed_text = f"Mode: {mode}" + (" [BOOST]" if state.a else "")
                    color = (0, 255, 255) if state.a else (0, 255, 0)
                    cv2.putText(img, speed_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    status = driver.get_status()
                    cv2.putText(img, f"Arm: {status.arm_status}", 
                               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv2.putText(img, f"Triggers: L={state.left_trigger:.1f} R={state.right_trigger:.1f}", 
                               (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    gripper_text = "CLOSE" if state.lb else ("OPEN" if state.rb else "-")
                    cv2.putText(img, f"Gripper: {gripper_text}", 
                               (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv2.imshow("RoboMaster Drive", img)
            
            # B button: stop recording (if recording)
            if recorder and state.b:
                click.echo("\n⏹️  Recording stopped (B button pressed)")
                break
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    break
                    
    except KeyboardInterrupt:
        pass
    
    finally:
        click.echo("\n🛑 Stopping robot...")
        driver.stop()
        driver.gripper_stop()
        driver.led_off()  # Turn off LEDs on exit
        
        if show_video:
            try:
                cv2.destroyAllWindows()
            except:
                pass
        
        click.echo("✓ Robot stopped")


def replay_loop(joystick: Joystick, driver: RobotDriver, player: CommandPlayer, show_video: bool,
                use_position_verification: bool = True):
    """Replay recorded commands with position verification and emergency stop.
    
    Args:
        joystick: Joystick for emergency stop (B button)
        driver: Robot driver
        player: CommandPlayer instance
        show_video: Whether to show video
        use_position_verification: Wait for position match instead of time-based (default True)
    """
    
    click.echo(f"\n▶️  Starting replay...")
    click.echo(f"   Duration: {player.duration:.1f}s")
    click.echo(f"   Commands: {len(player.commands)}")
    click.echo(f"   Position verification: {'ON' if use_position_verification else 'OFF'}")
    click.echo("   Press B button for EMERGENCY STOP")
    click.echo("   Press 'q' or ESC to quit\n")
    
    player.start()
    stopped_early = False
    last_cmd = None
    
    try:
        while player.is_playing:
            # Check for emergency stop (B button)
            state = joystick.get_state()
            
            if state.b:
                click.echo("\n🛑 EMERGENCY STOP (B button pressed)")
                stopped_early = True
                break
            
            # Execute commands based on mode
            if use_position_verification:
                # Position-based: get next command only if position matches
                cmd = player.get_next_command_with_position()
                if cmd:
                    player.execute_command(cmd, driver)
                    last_cmd = cmd
            else:
                # Time-based: execute pending commands
                pending = player.get_pending_commands()
                for cmd in pending:
                    player.execute_command(cmd, driver)
                    last_cmd = cmd
            
            # Video display with progress
            if show_video:
                img = driver.get_video_frame()
                if img is not None:
                    # Show replay progress
                    cv2.putText(img, "REPLAY MODE", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    progress = player.progress
                    elapsed = player.elapsed
                    cv2.putText(img, f"Progress: {progress:.0f}% ({elapsed:.1f}s / {player.duration:.1f}s)", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv2.putText(img, f"Commands: {player.current_index}/{len(player.commands)}", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Show position info
                    pos = player.current_position
                    cv2.putText(img, f"Pos: x={pos[0]:.2f}m y={pos[1]:.2f}m z={pos[2]:.1f}°", 
                               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    # Show waiting status
                    if player.is_waiting_for_position:
                        cv2.putText(img, "⏳ Waiting for position...", 
                                   (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    
                    cv2.putText(img, "Press B for EMERGENCY STOP", 
                               (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    
                    cv2.imshow("RoboMaster Replay", img)
            
            # Check for quit key
            key = cv2.waitKey(10) & 0xFF
            if key == ord('q') or key == 27:
                stopped_early = True
                break
            
            # Check pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stopped_early = True
                    break
                    
    except KeyboardInterrupt:
        stopped_early = True
    
    finally:
        player.stop()
        click.echo("\n🛑 Stopping robot...")
        driver.stop()
        driver.gripper_stop()
        driver.led_off()
        
        if show_video:
            try:
                cv2.destroyAllWindows()
            except:
                pass
        
        if stopped_early:
            click.echo("✓ Replay stopped early")
        else:
            click.echo("✓ Replay completed")


@click.command()
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
@click.option('--mode', '-m', default='continuous', 
              type=click.Choice(['continuous', 'step']),
              help='Movement mode: continuous (real-time) or step (discrete)')
@click.option('--resolution', '-res', default='360p',
              type=click.Choice(['360p', '540p', '720p']),
              help='Video resolution')
@click.option('--no-video', is_flag=True, help='Disable video feed')
@click.option('--simu', is_flag=True, help='Simulation mode (no robot connection)')
@click.option('--record', '-rec', default=None, 
              help='Record commands to file (JSON). Auto-names if just flag.')
@click.option('--replay', default=None, 
              help='Replay commands from JSON file. Use B button for emergency stop.')
def drive(local_ip, robot_ip, mode, resolution, no_video, simu, record, replay):
    """
    Drive the robot with a USB joystick.
    
    Designed for EP Engineering Robot.
    
    Controls:
    - Left stick: Move forward/backward and strafe
    - Right stick X: Rotate
    - D-pad: Arm control (up/down=Y, left/right=X)
    - Y button: Arm recenter
    - X button: Toggle LED
    - LB/RB: Gripper close/open
    - A: Speed boost
    
    Use --simu for simulation mode without robot connection.
    Press 'q' or ESC to quit.
    """
    
    # Initialize joystick
    click.echo("🎮 Initializing joystick...")
    try:
        joystick = Joystick()
        click.echo(f"✓ Joystick detected: {joystick.name}")
        click.echo(f"  Axes: {joystick.num_axes}, Buttons: {joystick.num_buttons}")
    except RuntimeError as e:
        click.echo(f"❌ {e}")
        return
    
    # Simulation mode
    if simu:
        run_simulation(joystick, mode)
        joystick.close()
        return
    
    # Replay mode
    if replay:
        import os
        if not os.path.exists(replay):
            click.echo(f"❌ Recording file not found: {replay}")
            joystick.close()
            return
        
        click.echo(f"📂 Loading recording: {replay}")
        try:
            player = CommandPlayer(replay)
            click.echo(f"   Recorded at: {player.recording.get('recorded_at', 'unknown')}")
            click.echo(f"   Duration: {player.duration:.1f}s")
            click.echo(f"   Commands: {len(player.commands)}")
        except Exception as e:
            click.echo(f"❌ Failed to load recording: {e}")
            joystick.close()
            return
        
        # Connect and replay
        base_driver = SDKDriver()
        try:
            click.echo("Connecting to robot...")
            base_driver.connect(local_ip, robot_ip)
            click.echo("✓ Connected!")
            
            # Subscribe to position for playback verification
            def replay_position_callback(x, y, z):
                player.update_position(x, y, z)
            
            if base_driver.subscribe_position(callback=replay_position_callback, freq=10):
                click.echo("📍 Position tracking enabled")
            
            # Start video if enabled
            show_video = not no_video
            if show_video:
                if base_driver.start_video(resolution):
                    click.echo(f"📹 Video stream started ({resolution})")
                else:
                    click.echo(f"⚠️  Video failed")
                    show_video = False
            
            # Run replay loop with position verification
            replay_loop(joystick, base_driver, player, show_video, use_position_verification=True)
            
        except RuntimeError as e:
            click.echo(f"❌ {e}")
        
        finally:
            base_driver.unsubscribe_position()
            base_driver.disconnect()
            joystick.close()
            click.echo("Connection closed.")
        return
    
    # Real robot drive mode
    base_driver = SDKDriver()
    recorder = None
    driver = base_driver
    
    try:
        click.echo("Connecting to robot...")
        base_driver.connect(local_ip, robot_ip)
        click.echo("✓ Connected!")
        
        # Report capabilities
        if base_driver.has_arm:
            click.echo("✓ Robotic arm detected")
        else:
            click.echo("⚠️  No robotic arm detected")
        
        if base_driver.has_gripper:
            click.echo("✓ Gripper detected")
        else:
            click.echo("⚠️  No gripper detected")
        
        # Setup recording if requested
        if record is not None:
            # If record is empty string (just flag), auto-generate name
            output_path = record if record else None
            recorder = CommandRecorder(output_path)
            driver = RecordingDriver(base_driver, recorder)
            
            # Subscribe to position for recording
            def record_position_callback(x, y, z):
                recorder.update_position(x, y, z)
            
            if base_driver.subscribe_position(callback=record_position_callback, freq=10):
                click.echo("📍 Position tracking enabled")
            
            recorder.start()
            click.echo(f"🔴 Recording to: {recorder.output_path}")
        
        # Start video if enabled
        show_video = not no_video
        if show_video:
            if base_driver.start_video(resolution):
                click.echo(f"📹 Video stream started ({resolution})")
            else:
                click.echo(f"⚠️  Video failed")
                show_video = False
        
        # Run drive loop
        drive_loop(joystick, driver, mode, show_video, recorder)
        
    except RuntimeError as e:
        click.echo(f"❌ {e}")
    
    finally:
        # Save recording if active
        if recorder and recorder.is_recording:
            recorder.stop()
            base_driver.unsubscribe_position()
            saved_path = recorder.save()
            click.echo(f"💾 Recording saved: {saved_path}")
        
        base_driver.disconnect()
        joystick.close()
        click.echo("Connection closed.")


if __name__ == '__main__':
    drive()
