# Dinit Quick Reference Card

## Service Templates

### Basic Process Service
```ini
type = process
command = /path/to/executable
logfile = /var/log/dinit/service_name.log
```

### Scripted Service (runs once)
```ini
type = scripted
command = /path/to/script.sh
logfile = /var/log/dinit/script_name.log
```

### Service with Dependencies
```ini
type = process
command = /usr/bin/myapp
logfile = /var/log/dinit/myapp.log
depends-on = database
waits-for = network
```

### Internal Service (no command)
```ini
type = internal
waits-for.d = services_directory
```

## Common Commands

```bash
# Test a service
python -m src.hud_controller.manual_dinit -d dinit.d service_name

# Start from boot service (all services)
python -m src.hud_controller.manual_dinit -d dinit.d boot

# Add service to boot sequence
cp dinit.d/my_service dinit.d/boot.d/
```

## Service Directives

| Directive | Values | Description |
|-----------|--------|-------------|
| type | process, scripted, internal | Service type |
| command | string | Command to execute |
| logfile | path | Output log location |
| depends-on | service_name | Hard dependency |
| waits-for | service_name | Soft dependency |
| waits-for.d | directory | Wait for all in dir (internal only) |

## Tips
- Process services run continuously
- Scripted services run once and exit
- Internal services are for grouping only
- All non-internal services need a logfile
- Use absolute paths in commands 