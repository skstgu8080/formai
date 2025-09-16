# GEMINI.md

## Project Overview

This project is **FormAI**, a high-performance browser automation platform built primarily in Rust. Its main purpose is to automate the filling of web forms, with a focus on speed, reliability, and bypassing anti-bot detection mechanisms.

The architecture consists of a **Rust backend** using the **Axum web framework** and a **static HTML/CSS/JavaScript frontend**.

**Key Technologies:**

*   **Backend:** Rust, Axum, Tokio, Playwright-rust
*   **Frontend:** HTML, Tailwind CSS, JavaScript
*   **Data Storage:** Local JSON files for profiles, field mappings, and other data.
*   **Build Tools:** Cargo for Rust, npm for frontend CSS building.

**Core Functionality:**

*   **High-Performance Automation:** The Rust backend provides significant performance improvements over traditional scripting languages.
*   **AI-Powered Form Analysis:** The application can use AI to analyze forms and map fields to profile data.
*   **Profile Management:** Users can create, manage, and use different profiles for form filling.
*   **Real-Time Updates:** A WebSocket connection provides real-time feedback on the automation process.
*   **Headless Browser Automation:** It uses Playwright to control a headless Chrome browser for automation tasks.

## Building and Running

The project can be run in two primary ways: natively for development or using Docker for production.

### Native Development

**Prerequisites:**

*   Rust (latest stable)
*   Node.js and npm
*   Chrome/Chromium browser

**Running the Application:**

1.  **Build CSS:**
    ```bash
    npm run build-css
    ```
2.  **Run the Backend:**
    *   On Windows, use the provided batch script:
        ```bash
        run.bat
        ```
    *   On Mac/Linux, use Cargo:
        ```bash
        cargo run --release
        ```

The application will be available at `http://localhost:5511`.

### Docker Deployment (Recommended for Production)

*   On Windows, use `start.bat`.
*   On Mac/Linux, a `start.sh` script is mentioned in the `README.md` but is not present in the file listing.

## Development Conventions

*   **Backend:** The Rust code is located in the `src` directory and follows standard Rust conventions. It's organized into modules for services, models, WebSocket handling, etc.
*   **Frontend:** The frontend is composed of static HTML files in the `templates` and `web` directories, CSS in the `static/css` directory, and JavaScript in the `static/js` directory.
*   **Styling:** The project uses **Tailwind CSS** for styling. The input CSS file is `static/css/input.css`, and the output is `static/css/tailwind.css`.
*   **Data:** Data is stored in JSON files in the `profiles`, `field_mappings`, and `saved_urls` directories.
*   **API:** The backend exposes a REST API for managing profiles, automation, and other resources. The API endpoints are defined in `src/main.rs`.
*   **AI Integration:** The application integrates with an AI service (via OpenRouter) for advanced form analysis. The relevant code is in `src/openrouter.rs`.
