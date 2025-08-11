# Python Backend for QnA Evaluator

This directory contains the Python implementation of the backend server.

## Setup

To run this server, you need to install the required dependencies.

```bash
pip install -r src/backend/requirements.txt
```

## Running the Server

Make sure you have your OpenAI API key and Project ID set as environment variables. You can either set them in your shell or create a `.env` file in the project root.

**.env file example:**
```
REACT_APP_GPT_KEY="your_openai_api_key_here"
REACT_APP_PROJECT_ID="your_openai_project_id_here"
```

Once the environment variables are set, you can run the local server:

```bash
python src/backend/py_local_api_server.py
```

The server will start on `http://localhost:3001` and will automatically reload when you make changes to the code.
