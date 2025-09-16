# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Server
- `start-rust.bat` - **RECOMMENDED: Start the Rust server (port 5511)**
- `cargo run --release` - Run Rust server directly (port 5511)
- `start.bat` - Legacy Python server (deprecated)

### Build System
- `npm run build-css` - Build Tailwind CSS from input.css to tailwind.css
- `npm run watch-css` - Watch and rebuild CSS automatically
- `cargo build --release` - Build optimized Rust executable
- `build-release.bat` - One-time build setup with CSS compilation

### Browser Setup
- `install-browser.bat` - Install Playwright browsers for automation

## Architecture Overview

FormAI is a **high-performance browser automation platform** built in Rust:

### Primary Architecture
**Rust Server** (`src/main.rs`)
- **Primary and recommended backend**
- Runs on port 5511
- Axum web framework with WebSocket support
- Full browser automation with Playwright
- AI-powered form field mapping
- Real-time progress updates
- Anti-bot detection bypass

### Frontend Structure
- **Web Pages**: `web/` directory contains HTML pages (index.html, profiles.html, automation.html, etc.)
- **Static Assets**: `static/` directory with CSS, JS, and images
- **CSS Build**: Uses Tailwind CSS with input.css → tailwind.css compilation
- **JavaScript**: Modular JS files in `static/js/` for different features

### Data Storage
- **Profiles**: JSON files in `profiles/` directory (auto-loaded on startup)
- **Field Mappings**: Stored in `field_mappings/` directory
- **Saved URLs**: Managed in `saved_urls/` directory
- **Recordings**: Browser recordings stored in `recordings/` directory

## Key Rust Modules

- `main.rs` - Axum server setup and routing
- `models.rs` - Data structures (Profile, FieldMapping, etc.)
- `services.rs` - Business logic and automation services
- `websocket.rs` - Real-time communication
- `field_mapping_service.rs` - Smart form field mapping
- `profile_adapter.rs` - Profile data transformation
- `stats.rs` - Performance tracking
- `dropdown_service.rs` - Dropdown handling automation

## Browser Automation

- Uses **Playwright** for reliable browser automation
- Headless Chrome/Chromium support
- Anti-bot detection bypass capabilities
- Form field detection and intelligent mapping
- Real-time progress updates via WebSocket

## Development Workflow

1. **Starting Server**: Run `start-rust.bat` for full-featured Rust server
2. **CSS Changes**: Run `npm run watch-css` for live CSS rebuilding
3. **Rust Changes**: Server will auto-rebuild when you restart `start-rust.bat`
4. **Testing**: Access via http://localhost:5511 (Rust server)

## Project Dependencies

### Rust Dependencies
- `axum` - Web framework with WebSocket support
- `playwright` - Browser automation
- `serde/serde_json` - Serialization
- `tokio` - Async runtime
- `sqlx` - Database operations

### Node.js Dependencies
- `tailwindcss` - CSS framework
- `playwright` - Browser automation support
- Shadcn UI components (configured in .cursor/mcp.json)

## Configuration Files

- `Cargo.toml` - Rust dependencies and build configuration
- `package.json` - Node.js scripts and dependencies
- `tsconfig.json` - TypeScript configuration
- `tailwind.config.js` - Tailwind CSS configuration
- `components.json` - Shadcn UI component configuration

## Performance Optimizations

The Rust server is optimized for production:
- Release profile with `opt-level = 3`
- Link-time optimization (LTO)
- Single codegen unit
- Panic = abort for smaller binaries
- Symbol stripping for reduced size

## Important Notes

- **Primary backend is Rust** - use `start-rust.bat` to start the server
- CSS must be built with `npm run build-css` after Tailwind changes
- Playwright browsers are automatically managed but can be manually installed
- Profile data is stored as JSON files, not in a traditional database
- WebSocket communication provides real-time automation updates
- The system includes anti-bot detection bypass capabilities for form automation
- AI models configured in `static/Models.json` for intelligent form field mapping

## Quick Start

1. **Run the server**: Double-click `start-rust.bat`
2. **Open dashboard**: Go to http://localhost:5511
3. **Start automation**: Profiles are automatically loaded from `profiles/` directory - just start using the web interface