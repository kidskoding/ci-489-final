# Kepler Path - Web Deployment Guide

The project is now ready for web deployment with user accounts and multiplayer support.

## Project Structure
- `server/`: Node.js backend
  - `server.js`: Express + WebSocket relay
  - `db.js`: SQLite user database
  - `public/`: Web frontend (Login, Dashboard, and the Game)
  - `public/game/`: The Pygame simulation compiled to WebAssembly (Wasm)

## How to Run Locally
1.  **Start the Server:**
    ```bash
    cd server
    node server.js
    ```
2.  **Access the Game:**
    Open your browser to [http://localhost:3000](http://localhost:3000)
3.  **Authentication:**
    - Create an account using the "Register" link.
    - Login with your new credentials.
4.  **Multiplayer:**
    - Open another tab or window at the same URL.
    - Login with a different user (or the same one).
    - Use the same Join Code in the game menu to connect!

## Deployment to Production

### 1. Static Game (GitHub Pages)
I have added a GitHub Actions workflow in `.github/workflows/deploy.yml`. 
- When you push to the `main` branch, it will automatically build your game and deploy it to a `gh-pages` branch.
- To finish setup:
  1. Go to your GitHub Repo -> Settings -> Pages.
  2. Set the Source to "Deploy from a branch".
  3. Select the `gh-pages` branch and `/ (root)` folder.

### 2. Backend (Render/Railway/etc.)
Since GitHub Pages is **static**, it cannot run your Node.js server (which handles logins and multiplayer).
- Deploy the `/server` folder to a service like **Render** or **Railway**.
- Update the WebSocket URL in your game if your server uses a different domain.

### 3. Integration
You can now point your `server/public/play.html` iframe to your GitHub Pages URL:
`<iframe src="https://your-username.github.io/your-repo-name/"></iframe>`
