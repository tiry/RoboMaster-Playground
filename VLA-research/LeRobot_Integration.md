# LeRobot + RoboMaster Integration

## What's This About?

I want to connect my DJI RoboMaster EP robot to HuggingFace's LeRobot framework and see if I can teach it to do useful things through imitation learning.

**The Goal:** Train a model to navigate around my place, pick up objects, and move them somewhere else.

**The Plan:** Start with simple standalone scripts. If it works well, maybe turn it into a proper LeRobot plugin later.

---

## 1. Why Am I Doing This?

### 1.1 The Real Reasons
- I have a RoboMaster EP sitting in a closet
- I want an excuse to play with LeRobot
- This is a learning experience — let's see what happens!

### 1.2 The Challenges
- RoboMaster uses high-level position commands (not joint-level control)
- Communication over WiFi adds latency (~50-100ms roundtrip)
- Can't move the robot by hand to record demonstrations (no kinesthetic teaching)

### 1.3 Why It Might Still Work
- For mobile manipulation, position-level control at 10-20Hz should be enough
- Navigation and grabbing things don't need millisecond precision
- The hope is we can still control the robot well enough to make it do stuff...

---

## 2. Scope

### 2.1 Phase 1 - Keep It Simple

| Component | What It Does |
|-----------|--------------|
| **Teleoperation** | Control robot with a gamepad (chassis + arm + gripper) |
| **Recording** | Save demonstrations in LeRobotDataset v3.0 format |
| **Training** | Use LeRobot's existing pipelines (ACT, Diffusion, etc.) |
| **Deployment** | Run the trained policy on the robot |

### 2.2 Not Doing (For Now)

- Full LeRobot CLI integration (`lerobot-record --robot.type=robomaster`)
- Multi-robot stuff
- Simulation
- Fancy teleoperation (VR, phone tilt controls)

### 2.3 Maybe Later (Phase 2)

- Native `lerobot-record` and `lerobot-deploy` support
- Teleop abstraction for different input devices
- Contribute `RoboMasterRobot` class to LeRobot codebase (if it makes sense)

---

## 3. The Task

### 3.1 What I Want The Robot To Do
```
Navigate from the living room to the kitchen, 
pick up a red cup from the counter, 
bring it to the dining table, 
and put it down.
```

### 3.2 Breaking It Down

| Step | What Happens | The Hard Part |
|------|--------------|---------------|
| **Navigate** | Drive from room A to room B | Seeing where to go, not hitting things |
| **Approach** | Get close to the target object | Finding the object, positioning precisely |
| **Grasp** | Move arm, close gripper | Getting the arm in the right spot |
| **Transport** | Drive while holding the object | Not dropping it, not crashing |
| **Place** | Position arm, open gripper | Putting it down in the right spot |

### 3.3 What Would "Success" Look Like?
- Robot completes the task 70%+ of the time
- Takes less than 3 minutes per run
- Works with different objects (similar size)

---

## 4. Technical Architecture

### 4.1 How It All Fits Together

```
┌─────────────────────────────────────────────────────────────────┐
│                        Training Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌───────────────┐    ┌──────────────────────┐  │
│  │ Gamepad  │───▶│ Teleoperation │───▶│ LeRobotDataset v3.0  │  │
│  └──────────┘    │    Script     │    │  (Parquet + MP4)     │  │
│                  └───────────────┘    └──────────┬───────────┘  │
│                                                   │              │
│                                                   ▼              │
│                                       ┌──────────────────────┐  │
│                                       │  LeRobot Training    │  │
│                                       │  (ACT / Diffusion)   │  │
│                                       └──────────┬───────────┘  │
│                                                   │              │
│                                                   ▼              │
│                                       ┌──────────────────────┐  │
│                                       │   Trained Policy     │  │
│                                       │   (HuggingFace Hub)  │  │
│                                       └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       Deployment Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ RoboMaster EP    │◀───│  Deployment  │◀───│ Trained Model │  │
│  │ (WiFi/USB)       │    │    Script    │    │               │  │
│  └──────────────────┘    └──────────────┘    └───────────────┘  │
│           │                     ▲                               │
│           │                     │                               │
│           ▼                     │                               │
│  ┌──────────────────┐          │                               │
│  │ Camera + Sensors │──────────┘                               │
│  │ (Observations)   │                                          │
│  └──────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Data Flow

```
What the robot sees/feels (10-20 Hz):
├── observation.images.front    # 640x480 camera image
├── observation.state           # arm position, chassis velocity, IMU
└── timestamp

What the policy outputs:
├── action                      # chassis speed, arm target, gripper
```

### 4.3 Code Structure

```
robomaster_lerobot/
├── __init__.py
├── cli.py                # Unified CLI (click)
├── robot.py              # RoboMaster wrapper
├── teleop.py             # Gamepad control logic
├── recorder.py           # Recording logic
├── deployer.py           # Policy deployment logic
├── config.py             # Configuration
├── utils.py              # Helpers
├── tests/
│   ├── test_connection.py
│   └── test_teleop.py
└── README.md
```

### 4.4 CLI Design

Single CLI entry point (`robomaster`) with subcommands:

| Command | What It Does |
|---------|--------------|
| `robomaster teleop` | Drive the robot with gamepad (no recording) |
| `robomaster record` | Drive + save to local LeRobotDataset |
| `robomaster push` | Upload local dataset to HuggingFace Hub |
| `robomaster deploy` | Run a trained policy (from local or HF) |

**Data Flow:**

```
Recording:   teleop → local directory → (optional) push to HF Hub
Training:    local dataset or HF → lerobot-train → model
Deployment:  local model or HF → robot
```

Everything is local-first. HuggingFace Hub is optional for sharing/cloud training.

---

## 5. Key Interfaces

### 5.1 Robot Wrapper

A `RoboMasterRobot` class that wraps the SDK with a simple interface:
- `connect()` / `disconnect()` — manage connection
- `get_observation()` — returns camera image + sensor state
- `send_action()` — sends chassis velocity, arm target, gripper command

### 5.2 Dataset Structure

Observations (what the robot sees):
- **Image:** 640x480 front camera
- **State:** arm position (x, y), chassis velocity (x, y, z), IMU (pitch, roll, yaw)

Actions (what the policy outputs):
- Chassis velocity (x, y, z)
- Arm target position (x, y)
- Gripper (open/close)

---

## 6. How To Use It

### 6.1 Setup
```bash
# Install the integration
pip install -e .

# This gives you the `robomaster` CLI command
```

### 6.2 Test Teleoperation
```bash
# Just drive around with gamepad, no recording
robomaster teleop --robot-ip 192.168.2.1
```

### 6.3 Record Demonstrations
```bash
# Drive and record to a local directory
robomaster record \
    --robot-ip 192.168.2.1 \
    --output-dir ./data/fetch-task \
    --task "Pick up red cup and place on table" \
    --num-episodes 50
```

### 6.4 (Optional) Push to HuggingFace Hub
```bash
# If you want to share the dataset or train on cloud
robomaster push \
    --dataset-dir ./data/fetch-task \
    --repo-id your-username/robomaster-fetch
```

### 6.5 Train
```bash
# Train from local dataset
lerobot-train \
    --policy=act \
    --dataset.path=./data/fetch-task \
    --output_dir=./models/fetch-policy

# Or from HuggingFace Hub (if you pushed it)
lerobot-train \
    --policy=act \
    --dataset.repo_id=your-username/robomaster-fetch \
    --output_dir=./models/fetch-policy
```

### 6.6 Deploy
```bash
# Run from local model
robomaster deploy \
    --robot-ip 192.168.2.1 \
    --policy ./models/fetch-policy

# Or from HuggingFace Hub
robomaster deploy \
    --robot-ip 192.168.2.1 \
    --policy your-username/robomaster-fetch-policy
```

---

## 7. Risks

| What Could Go Wrong | How Likely | What To Do About It |
|---------------------|------------|---------------------|
| Robot doesn't work after years in closet | Unknown | Hope for the best, buy new battery |
| WiFi latency messes up control | Medium | Use USB connection as fallback |
| Arm not precise enough to grab things | Medium | Use bigger objects, be less picky |
| Camera too slow | Low | Lower resolution, optimize code |

---

## 8. Milestones

### Phase 1 Done When:
- [ ] Can drive robot around with gamepad
- [ ] Can record 10+ episodes
- [ ] LeRobot training runs
- [ ] Policy runs on robot (even if badly)

### Actually Successful When:
- [ ] Robot does the fetch task 70% of the time
- [ ] Someone else could follow the docs and replicate it

---

## 9. Simulation Option

There's an existing simulator that works with the RoboMaster EP:

**`jeguzzi/robomaster_sim`** — https://github.com/jeguzzi/robomaster_sim

- Uses CoppeliaSim for physics/visualization
- **Works with the same official RoboMaster SDK** — same Python API
- Your teleop code works in sim AND on real robot unchanged
- Updated Oct 2025

This means once we have teleoperation working, we can:
1. Install CoppeliaSim + robomaster_sim
2. Test/iterate on recording and policies in simulation
3. Transfer directly to real robot

---

## 10. Open Questions

1. **Gripper feedback:** Can we tell if we're actually holding something?
2. **More cameras:** Would a wrist camera help with grasping?
3. **Multiple tasks:** Focus on one task or try several?

---

## 11. Next Steps

1. [ ] Review this spec
2. [ ] Find the RoboMaster box in the closet and hope it still works
3. [ ] Set up dev environment
4. [ ] Get basic teleoperation working (gamepad → robot)
5. [ ] **(Addon)** Set up simulation with robomaster_sim + CoppeliaSim
6. [ ] Build the robot wrapper (clean interface)
7. [ ] Build recording pipeline
8. [ ] Record some demos
9. [ ] Train a model
10. [ ] See if it works!

---

*Last Updated: January 26, 2026*
