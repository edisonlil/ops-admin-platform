# OPS-CLI

OPS Admin Platform Project Manager - A CLI tool for creating and managing projects from the ops-admin-platform scaffold.

## Installation

```bash
pip install ops-cli
```

## Features

- **Interactive Project Creation**: Create new projects with branch selection and module selection
- **Project Management**: List, switch, and remove projects
- **Environment Management**: Automatic virtual environment and Node.js dependencies setup
- **Module Selection**: Choose which DDD modules to enable in your project

## Usage

### Create a new project

```bash
ops-cli init
```

This will:
1. Fetch available branches from the scaffold repository
2. Let you select which branch to use
3. Let you select which modules to enable
4. Ask for a project name
5. Clone the repository and setup the project

### Setup project

```bash
ops-cli setup
```

Configure database and run initialization scripts.

### Start project

```bash
ops-cli run
```

Start backend and frontend in development mode.

### Deploy project

```bash
# Add deploy target
ops-cli deploy --add

# List deploy targets
ops-cli deploy --list-targets

# Deploy to target
ops-cli deploy --target prod

# Remove deploy target
ops-cli deploy --remove prod
```

Deploy builds Docker image, packages with frontend dist, and deploys via SSH.

### List all projects

```bash
ops-cli list
```

### Switch to a project

```bash
ops-cli switch my-project
```

### Show project status

```bash
ops-cli status
```

### Remove a project

```bash
ops-cli remove my-project
```

### Show configuration

```bash
ops-cli config
```

## Configuration

Configuration is stored in `~/.ops-cli/config.json`:

```json
{
  "scaffold_url": "https://github.com/edisonlil/ops-admin-platform.git",
  "projects_dir": "~/OpsPyProject",
  "projects": {},
  "current_project": null
}
```

## Available Modules

- system - Core system functionality
- cron - Scheduled tasks
- identity_access - User management and authentication
- organization - Organizational structure
- authorization - Role-based access control
- basic_data - Basic data management
- file_management - File storage and management
- messaging - Notification system
- llm_runtime - LLM integration
- ai_assets - AI asset management
- ai_applications - AI application management
- ai_capabilities - AI capabilities
- appearance - UI/Theme customization

## License

MIT