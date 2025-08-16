# Question Creator

A visual editor for creating and managing business questionnaires with AI evaluation capabilities.

## Features

- 📝 Visual question editor with live preview
- 🤖 AI-powered question evaluation  
- 🎯 Multiple question types (text, multi-choice, yes/no, etc.)
- 📁 Save/load questionnaires
- 🔄 Drag & drop question reordering
- 🎨 Resizable panels
- 🌐 Cloudflare Tunnel support for secure remote access

## Quick Start

### 1. Configure Services

Edit `config.json` to set your network configuration:
```json
{
  "backend": {
    "host": "192.168.1.50",  // Your IP address
    "port": 3004              // Backend port
  },
  "frontend": {
    "host": "192.168.1.50",  // Your IP address  
    "port": 3003              // Frontend port
  }
}
```

### 2. Generate Configurations

```bash
# Generate Cloudflare and environment configs
python3 cloudflare-config-generator.py
```

### 3. Start Services

```bash
# Terminal 1: Start backend
./start-backend.sh

# Terminal 2: Start frontend
npm install  # First time only
npm start
```

### 4. Access Application

- **Local**: http://localhost:3003
- **Network**: http://192.168.1.50:3003
- **Cloudflare**: https://creator.predictex.ai

## Configuration Management

All configuration is centralized in `config.json`. To change backend address or port:

1. Edit `config.json`
2. Run `python3 cloudflare-config-generator.py`
3. Restart services

See [CONFIG_MANAGEMENT.md](CONFIG_MANAGEMENT.md) for detailed configuration guide.

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can’t go back!**

If you aren’t satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you’re on your own.

You don’t have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn’t feel obligated to use this feature. However we understand that this tool wouldn’t be useful if you couldn’t customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).
