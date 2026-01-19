# Laser Cutter Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use ed3d-plan-and-execute:subagent-driven-development to implement this plan task-by-task.

**Goal:** YAML-based configuration for machine/material power settings

**Architecture:** Create laser_profiles/ directory with YAML files defining power/speed settings per material and operation type. Load and validate profiles with clear error messages.

**Tech Stack:** PyYAML, Python dataclasses

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-18

---

## Phase 2: Laser Profile System

**Goal:** YAML-based configuration for machine/material power settings

**Done when:** Profiles load correctly, validation rejects malformed files, missing profiles produce clear errors

---

### Task 1: Add PyYAML dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add PyYAML to requirements**

Add to the end of `requirements.txt`:

```
PyYAML==6.0.2
```

**Step 2: Install the new dependency**

Run: `pip install PyYAML==6.0.2`

Expected: `Successfully installed PyYAML-6.0.2`

**Step 3: Verify installation**

Run: `python -c "import yaml; print(f'PyYAML version: {yaml.__version__}')"`

Expected: `PyYAML version: 6.0.2`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add PyYAML dependency for laser profile configuration"
```

---

### Task 2: Create laser profiles directory and default profile

**Files:**
- Create: `laser_profiles/p2_basswood_3mm.yaml`

**Step 1: Create the laser_profiles directory**

Run: `mkdir -p laser_profiles`

**Step 2: Create the default laser profile**

Create file `laser_profiles/p2_basswood_3mm.yaml`:

```yaml
# XTool P2 Laser Profile for 3mm Basswood Plywood
# Power values: 1-100 (percentage)
# Speed values: 1-400 (mm/s)
# Density values: 1-100 (lines per mm for raster operations)

machine: P2
material:
  name: "3mm Basswood Plywood"
  thickness: 3

operations:
  # Score mode - vector engraving for road lines
  score:
    roads_motorway:
      power: 25
      speed: 100
    roads_primary:
      power: 22
      speed: 120
    roads_secondary:
      power: 18
      speed: 140
    roads_tertiary:
      power: 15
      speed: 160
    roads_residential:
      power: 12
      speed: 180

  # Fill mode - raster engraving for areas
  engrave_fill:
    water:
      power: 40
      speed: 200
      density: 100
    parks:
      power: 30
      speed: 200
      density: 80

  # Solid engrave - for text elements
  engrave_solid:
    text:
      power: 50
      speed: 150
```

**Step 3: Verify the file was created**

Run: `cat laser_profiles/p2_basswood_3mm.yaml | head -5`

Expected:
```
# XTool P2 Laser Profile for 3mm Basswood Plywood
# Power values: 1-100 (percentage)
# Speed values: 1-400 (mm/s)
# Density values: 1-100 (lines per mm for raster operations)
```

**Step 4: Commit**

```bash
git add laser_profiles/
git commit -m "feat: add default laser profile for P2 with 3mm basswood

Includes power/speed settings for:
- Road scoring (5 tiers by importance)
- Water/parks raster engraving
- Text solid engraving"
```

---

### Task 3: Create laser_config.py with profile loading and validation

**Files:**
- Create: `laser_config.py`

**Step 1: Create the laser_config.py file**

```python
"""
Laser profile configuration module.

Loads and validates YAML-based laser profiles for XTool laser cutters.
"""
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
import yaml


LASER_PROFILES_DIR = "laser_profiles"


class LaserProfileError(Exception):
    """Exception for laser profile loading/validation errors."""
    pass


@dataclass
class LaserOperation:
    """Settings for a single laser operation."""
    power: int  # 1-100
    speed: int  # 1-400 mm/s
    density: Optional[int] = None  # 1-100, only for raster operations


@dataclass
class LaserProfile:
    """Complete laser profile with all operation settings."""

    machine: str
    material_name: str
    material_thickness: int

    # Score operations (roads)
    score_roads_motorway: LaserOperation
    score_roads_primary: LaserOperation
    score_roads_secondary: LaserOperation
    score_roads_tertiary: LaserOperation
    score_roads_residential: LaserOperation

    # Fill operations (water, parks)
    engrave_fill_water: LaserOperation
    engrave_fill_parks: LaserOperation

    # Solid operations (text)
    engrave_solid_text: LaserOperation


def get_available_profiles() -> list:
    """
    Get list of available laser profile names.

    Returns:
        List of profile names (without .yaml extension)
    """
    if not os.path.exists(LASER_PROFILES_DIR):
        return []

    profiles = []
    for file in sorted(os.listdir(LASER_PROFILES_DIR)):
        if file.endswith('.yaml') or file.endswith('.yml'):
            profile_name = os.path.splitext(file)[0]
            profiles.append(profile_name)

    return profiles


def _validate_operation(op_data: Dict, op_name: str,
                        require_density: bool = False) -> LaserOperation:
    """
    Validate and create a LaserOperation from dict data.

    Args:
        op_data: Dictionary with power, speed, and optionally density
        op_name: Name of operation for error messages
        require_density: Whether density is required

    Returns:
        LaserOperation instance

    Raises:
        LaserProfileError: If validation fails
    """
    if not isinstance(op_data, dict):
        raise LaserProfileError(
            f"Operation '{op_name}' must be a dictionary with power/speed keys"
        )

    # Validate power
    power = op_data.get('power')
    if power is None:
        raise LaserProfileError(f"Operation '{op_name}' missing required 'power' key")
    if not isinstance(power, int) or not 1 <= power <= 100:
        raise LaserProfileError(
            f"Operation '{op_name}' power must be integer 1-100, got: {power}"
        )

    # Validate speed
    speed = op_data.get('speed')
    if speed is None:
        raise LaserProfileError(f"Operation '{op_name}' missing required 'speed' key")
    if not isinstance(speed, int) or not 1 <= speed <= 400:
        raise LaserProfileError(
            f"Operation '{op_name}' speed must be integer 1-400, got: {speed}"
        )

    # Validate density (optional or required depending on operation)
    density = op_data.get('density')
    if require_density and density is None:
        raise LaserProfileError(
            f"Operation '{op_name}' missing required 'density' key for fill operation"
        )
    if density is not None:
        if not isinstance(density, int) or not 1 <= density <= 100:
            raise LaserProfileError(
                f"Operation '{op_name}' density must be integer 1-100, got: {density}"
            )

    return LaserOperation(power=power, speed=speed, density=density)


def load_laser_profile(profile_name: str) -> LaserProfile:
    """
    Load and validate a laser profile from YAML file.

    Args:
        profile_name: Name of profile (without .yaml extension)

    Returns:
        LaserProfile instance with validated settings

    Raises:
        LaserProfileError: If profile not found or validation fails
    """
    # Check if profiles directory exists
    if not os.path.exists(LASER_PROFILES_DIR):
        raise LaserProfileError(
            f"Laser profiles directory '{LASER_PROFILES_DIR}' not found"
        )

    # Find the profile file
    yaml_path = os.path.join(LASER_PROFILES_DIR, f"{profile_name}.yaml")
    yml_path = os.path.join(LASER_PROFILES_DIR, f"{profile_name}.yml")

    if os.path.exists(yaml_path):
        profile_path = yaml_path
    elif os.path.exists(yml_path):
        profile_path = yml_path
    else:
        available = get_available_profiles()
        if available:
            raise LaserProfileError(
                f"Laser profile '{profile_name}' not found. "
                f"Available profiles: {', '.join(available)}"
            )
        else:
            raise LaserProfileError(
                f"Laser profile '{profile_name}' not found. "
                f"No profiles available in '{LASER_PROFILES_DIR}'"
            )

    # Load YAML
    try:
        with open(profile_path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            raise LaserProfileError(
                f"YAML parsing error in '{profile_path}' at line {mark.line + 1}, "
                f"column {mark.column + 1}: {e.problem}"
            )
        raise LaserProfileError(f"YAML parsing error in '{profile_path}': {e}")

    if not isinstance(data, dict):
        raise LaserProfileError(f"Profile '{profile_path}' must be a YAML dictionary")

    # Validate top-level structure
    if 'machine' not in data:
        raise LaserProfileError(f"Profile missing required 'machine' key")
    if 'material' not in data:
        raise LaserProfileError(f"Profile missing required 'material' key")
    if 'operations' not in data:
        raise LaserProfileError(f"Profile missing required 'operations' key")

    # Validate material
    material = data['material']
    if not isinstance(material, dict):
        raise LaserProfileError("'material' must be a dictionary")
    if 'name' not in material:
        raise LaserProfileError("material missing required 'name' key")
    if 'thickness' not in material:
        raise LaserProfileError("material missing required 'thickness' key")

    # Validate operations
    ops = data['operations']
    if not isinstance(ops, dict):
        raise LaserProfileError("'operations' must be a dictionary")

    # Validate score operations
    if 'score' not in ops:
        raise LaserProfileError("operations missing required 'score' section")
    score = ops['score']
    required_roads = ['roads_motorway', 'roads_primary', 'roads_secondary',
                      'roads_tertiary', 'roads_residential']
    for road in required_roads:
        if road not in score:
            raise LaserProfileError(f"operations.score missing required '{road}'")

    # Validate engrave_fill operations
    if 'engrave_fill' not in ops:
        raise LaserProfileError("operations missing required 'engrave_fill' section")
    engrave_fill = ops['engrave_fill']
    for area in ['water', 'parks']:
        if area not in engrave_fill:
            raise LaserProfileError(
                f"operations.engrave_fill missing required '{area}'"
            )

    # Validate engrave_solid operations
    if 'engrave_solid' not in ops:
        raise LaserProfileError("operations missing required 'engrave_solid' section")
    engrave_solid = ops['engrave_solid']
    if 'text' not in engrave_solid:
        raise LaserProfileError("operations.engrave_solid missing required 'text'")

    # Build and return LaserProfile
    print(f"✓ Loaded laser profile: {data['machine']} / {material['name']}")

    return LaserProfile(
        machine=data['machine'],
        material_name=material['name'],
        material_thickness=material['thickness'],

        score_roads_motorway=_validate_operation(
            score['roads_motorway'], 'score.roads_motorway'),
        score_roads_primary=_validate_operation(
            score['roads_primary'], 'score.roads_primary'),
        score_roads_secondary=_validate_operation(
            score['roads_secondary'], 'score.roads_secondary'),
        score_roads_tertiary=_validate_operation(
            score['roads_tertiary'], 'score.roads_tertiary'),
        score_roads_residential=_validate_operation(
            score['roads_residential'], 'score.roads_residential'),

        engrave_fill_water=_validate_operation(
            engrave_fill['water'], 'engrave_fill.water', require_density=True),
        engrave_fill_parks=_validate_operation(
            engrave_fill['parks'], 'engrave_fill.parks', require_density=True),

        engrave_solid_text=_validate_operation(
            engrave_solid['text'], 'engrave_solid.text'),
    )
```

**Step 2: Verify the module imports correctly**

Run: `python -c "from laser_config import load_laser_profile, get_available_profiles, LaserProfileError; print('Import successful')"`

Expected: `Import successful`

**Step 3: Commit**

```bash
git add laser_config.py
git commit -m "feat: add laser profile loading with validation

- LaserProfile and LaserOperation dataclasses
- load_laser_profile() with comprehensive validation
- get_available_profiles() for CLI discovery
- Clear error messages for malformed profiles"
```

---

### Task 4: Verify profile loading works correctly

**Files:**
- None (verification only)

**Step 1: Test successful profile loading**

Run: `python -c "from laser_config import load_laser_profile; p = load_laser_profile('p2_basswood_3mm'); print(f'Machine: {p.machine}'); print(f'Material: {p.material_name}'); print(f'Motorway power: {p.score_roads_motorway.power}')"`

Expected:
```
✓ Loaded laser profile: P2 / 3mm Basswood Plywood
Machine: P2
Material: 3mm Basswood Plywood
Motorway power: 25
```

**Step 2: Test missing profile error**

Run: `python -c "from laser_config import load_laser_profile, LaserProfileError;
try:
    load_laser_profile('nonexistent')
except LaserProfileError as e:
    print(f'Error (expected): {e}')"`

Expected: `Error (expected): Laser profile 'nonexistent' not found. Available profiles: p2_basswood_3mm`

**Step 3: Test get_available_profiles**

Run: `python -c "from laser_config import get_available_profiles; print(get_available_profiles())"`

Expected: `['p2_basswood_3mm']`

---

### Task 5: Test validation rejects malformed profiles

**Files:**
- Create: `laser_profiles/test_invalid.yaml` (temporary)

**Step 1: Create a malformed profile for testing**

Create temporary file `laser_profiles/test_invalid.yaml`:

```yaml
machine: TestMachine
material:
  name: "Test Material"
  thickness: 3
operations:
  score:
    roads_motorway:
      power: 200  # Invalid: > 100
      speed: 100
```

**Step 2: Verify validation catches the error**

Run: `python -c "from laser_config import load_laser_profile, LaserProfileError;
try:
    load_laser_profile('test_invalid')
except LaserProfileError as e:
    print(f'Validation error (expected): {e}')"`

Expected: `Validation error (expected): Operation 'score.roads_motorway' power must be integer 1-100, got: 200`

**Step 3: Clean up test file**

Run: `rm laser_profiles/test_invalid.yaml`

**Step 4: Verify existing PNG generation still works**

Run: `python create_map_poster.py --list-themes`

Expected: Lists all themes without errors (laser config doesn't interfere)

---

## Phase 2 Complete

After completing all tasks:
- `laser_profiles/` directory exists with `p2_basswood_3mm.yaml`
- `laser_config.py` provides `load_laser_profile()` and `get_available_profiles()`
- Validation catches malformed profiles with clear error messages
- Missing profiles list available alternatives
- Ready for Phase 3: Laser Theme Extension
