# Kepler Path - Web Deployment Guide

The project is now ready for web deployment with user accounts and multiplayer support.

## Project Structure
- `server/`: Node.js backend
  - `server.js`: Express + WebSocket relay
  - `db.js`: SQLite user database
  - `public/`: Web frontend (Login, Dashboard, and the Game)
  - `public/game/`: The Pygame simulation compiled to WebAssembly (Wasm)

## How to Run Locally
1.  **Build the browser game:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    make install-build
    make web
    ```
    The static build is written to `build/web/`.
2.  **Start the Server:**
    ```bash
    cd server
    npm install
    npm start
    ```
3.  **Access the Game:**
    Open your browser to [http://localhost:3000](http://localhost:3000)
4.  **Authentication:**
    - Create an account using the "Register" link.
    - Login with your new credentials.
5.  **Multiplayer:**
    - Open another tab or window at the same URL.
    - Login with a different user (or the same one).
    - Use the same Join Code in the game menu to connect!

## Free Production Deployment

This project should be deployed as two free services:
- GitHub Pages hosts the static Pygame/pygbag browser build.
- Render Free Web Service hosts the Node login page and WebSocket relay.

### 1. Static Game on GitHub Pages
The GitHub Actions workflow in `.github/workflows/deploy.yml` builds the Pygame app with `pygbag`.
- When you push to the `main` branch, it will automatically build your game and deploy it with GitHub Pages.
- To finish setup:
  1. Go to your GitHub repo's Settings -> Pages.
  2. Set the Source to "GitHub Actions".
  3. Push to `main` and wait for the deployment workflow to finish.
  4. Copy the deployed Pages URL. It should look like `https://your-username.github.io/your-repo-name/`.

### 2. WebSocket Backend on Render Free
Render can run the Node server and accept WebSocket connections. The `render.yaml` file in this repo defines the free web service.

1. Commit and push this repo to GitHub.
2. In Render, choose **New -> Blueprint**.
3. Connect the GitHub repo and let Render use `render.yaml`.
4. After the service is created, open its environment variables.
5. Set `GAME_URL` to your GitHub Pages URL.
6. Keep `ENABLE_DISCOVERY=false`.
7. Let Render deploy the service.

The final playable URL is the Render service URL, for example:

```text
https://kepler-path-relay.onrender.com
```

Students open that Render URL, log in, and the page embeds the GitHub Pages game while passing the Render host as the WebSocket relay.

### Free-Tier Tradeoffs
- Render Free can sleep after inactivity, so the first load may take a little while.
- Use one Render instance. Multiple instances require shared room state, which means Redis or another paid/shared service.
- The included SQLite auth database is fine for a demo, but free Render instances do not guarantee durable local disk forever. For a class demo, that is usually acceptable.

### Manual Render Settings

If you create the service manually instead of using the Blueprint, use:

```text
Runtime: Node
Root Directory: server
Build Command: npm install
Start Command: npm start
Plan: Free
```

Environment variables:

```text
NODE_VERSION=22
GAME_URL=https://kidskoding.github.io/ci-489-final/
ENABLE_DISCOVERY=false
JWT_SECRET=<long random string>
```
