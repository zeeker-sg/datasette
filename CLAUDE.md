# Claude Code Configuration

This file helps Claude understand your project structure and preferences.

## Project Overview
This appears to be a Zeeker Datasette project - a data exploration tool built on Datasette with custom plugins, templates, and styling.

## Key Files and Structure
- `pyproject.toml` - Python project configuration with dependencies
- `plugins/` - Custom Datasette plugins for enhanced functionality
- `templates/` - HTML templates for the web interface
- `static/` - CSS, JavaScript, and image assets
- `scripts/` - Utility scripts including S3 downloads and management
- `tests/` - Test suite with pytest configuration

## Development Commands
Based on the project structure, common commands likely include:
- `uv sync` - Install dependencies using uv
- `pytest` - Run the test suite
- `datasette .` - Run the Datasette server locally

## Dependencies
- Uses `uv` for Python dependency management
- Built on Datasette framework
- Includes custom plugins and templates
- Docker support available via Dockerfile and docker-compose.yml

## Notes
- Project uses modern Python tooling with uv and pyproject.toml
- Appears to be focused on legal/court data based on static assets
- Has S3 integration for data downloads
- Includes comprehensive test coverage