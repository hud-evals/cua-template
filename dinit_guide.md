# Dinit Service Management Guide

## Table of Contents
1. [What is Dinit?](#what-is-dinit)
2. [How manual_dinit.py Works](#how-manual_dinitpy-works)
3. [Service Types](#service-types)
4. [Service Definition Format](#service-definition-format)
5. [How to Add New Services](#how-to-add-new-services)
6. [Examples](#examples)

## What is Dinit?

Dinit is a service supervisor/init system (similar to systemd or SysV init) that manages the starting and stopping of system services. It ensures services start in the correct order based on their dependencies and keeps them running.

Key features of dinit:
- **Dependency management**: Services can depend on other services
- **Service supervision**: Monitors running services and can restart them if they fail
- **Parallel startup**: Services without dependencies can start simultaneously
- **Simple configuration**: Uses plain text files for service definitions

## How manual_dinit.py Works

The `manual_dinit.py` file is a simplified Python implementation of dinit's core functionality. It consists of three main components:

### 1. Service Class
```python
@dataclass
class Service:
    name: str
    type: str = "process"  # process | scripted | internal
    command: Optional[str] = None
    logfile: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
```

### 2. ServiceLoader Class
- Reads service definition files from a directory (typically `/etc/dinit.d/` or `dinit.d/`)
- Parses the key-value format of service files
- Handles special directives like `waits-for.d` for internal services
- Recursively loads dependencies

### 3. SimpleDinit Class
- Manages the actual starting of services
- Ensures dependencies are started before dependent services
- Detects circular dependencies
- Runs services based on their type:
  - **process**: Long-running services (uses `subprocess.Popen`)
  - **scripted**: One-time scripts (uses `subprocess.run`)
  - **internal**: Meta-services with no actual command

## Service Types

### 1. Process Services
- Long-running services that stay active
- Started with `subprocess.Popen`
- Examples: web servers, VNC servers, X servers
- Must specify a `logfile` for output

### 2. Scripted Services
- Run once and complete
- Started with `subprocess.run`
- Examples: initialization scripts, setup commands
- Must specify a `logfile` for output

### 3. Internal Services
- Meta-services that don't run any command
- Used for grouping dependencies
- Can use `waits-for.d` to wait for all services in a directory
- Example: the `boot` service

## Service Definition Format

Service files use a simple key-value format:
```
key = value
# or
key : value
```

### Common Directives

| Directive | Description | Required |
|-----------|-------------|----------|
| `type` | Service type: process, scripted, or internal | No (default: process) |
| `command` | Command to execute | Yes (except for internal) |
| `logfile` | Path to log file for output | Yes (except for internal) |
| `depends-on` | Service that must start before this one | No |
| `waits-for` | Service to wait for (adds to dependencies) | No |
| `waits-for.d` | Directory of services to wait for (internal only) | No |

### Additional Directives (recognized but not implemented in manual_dinit)
- `smooth-recovery`: Smooth recovery mode
- `restart`: Auto-restart on failure

## How to Add New Services

### Step 1: Create a Service File
Create a new file in the `dinit.d/` directory with your service name:

```bash
touch dinit.d/my_service
```

### Step 2: Define the Service
Edit the file and add the service definition:

#### Example: Process Service
```ini
# dinit.d/my_web_server
type = process
command = python -m http.server 8080
logfile = /var/log/dinit/my_web_server.log
```

#### Example: Scripted Service
```ini
# dinit.d/setup_database
type = scripted
command = /usr/bin/setup_db.sh
logfile = /var/log/dinit/setup_database.log
```

#### Example: Service with Dependencies
```ini
# dinit.d/my_app
type = process
command = /usr/bin/my_app
logfile = /var/log/dinit/my_app.log
depends-on = setup_database
waits-for = my_web_server
```

### Step 3: Add to Boot Sequence (Optional)
To make your service start automatically:

1. Copy your service file to `dinit.d/boot.d/`:
   ```bash
   cp dinit.d/my_service dinit.d/boot.d/
   ```

2. Or add it as a dependency to another service that's already in the boot sequence

### Step 4: Test Your Service
Run the service manually:
```bash
python -m src.hud_controller.manual_dinit -d dinit.d my_service
```

## Examples

### Current Service Structure in psyopbench

The psyopbench project uses dinit to manage its display and VNC services:

```
dinit.d/
├── boot              # Main entry point (internal service)
├── boot.d/           # Services to start at boot
│   ├── mk_xauth      # Creates X authority file
│   ├── websockify    # WebSocket to TCP proxy for noVNC
│   ├── x11vnc        # VNC server
│   ├── xfce4_session # XFCE desktop environment
│   └── xvfb          # Virtual framebuffer X server
```

**Boot sequence:**
1. `boot` (internal) → waits for all services in `boot.d/`
2. `xvfb` starts first (no dependencies)
3. `mk_xauth` runs (scripted, sets up X authentication)
4. `x11vnc` starts after `xvfb` (depends on X server)
5. `xfce4_session` starts (desktop environment)
6. `websockify` starts (for web-based VNC access)

### Adding a New Service Example

Let's add a service to start the psyopbench backend:

```ini
# dinit.d/psyopbench_backend
type = process
command = cd /mcp_server && uvicorn main:app --port 8000
logfile = /var/log/dinit/psyopbench_backend.log
waits-for = xvfb  # Ensure display is ready
```

To include it in boot:
```bash
cp dinit.d/psyopbench_backend dinit.d/boot.d/
```

### Debugging Services

1. **Check logs**: Service output is written to the specified logfile
2. **Run manually**: Use `python -m src.hud_controller.manual_dinit -d dinit.d <service_name>`
3. **Enable debug logging**: The script uses Python's logging module
4. **Check dependencies**: Ensure all required services are defined

## Best Practices

1. **Always specify logfiles** for process and scripted services
2. **Use descriptive service names** that indicate their function
3. **Document dependencies** clearly in comments
4. **Test services individually** before adding to boot sequence
5. **Keep commands simple** - use shell scripts for complex setups
6. **Use absolute paths** in commands when possible
7. **Create log directory** `/var/log/dinit/` before running services

## Limitations of manual_dinit.py

Compared to the full dinit implementation, manual_dinit.py:
- Only supports starting services (no stop/restart)
- Doesn't implement service monitoring/auto-restart
- Ignores some directives (smooth-recovery, restart)
- Basic error handling
- No socket activation or advanced features

However, it provides the core functionality needed for basic service management and dependency resolution. 