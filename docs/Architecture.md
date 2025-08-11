# QnA Evaluator: Architecture Overview

**Document Generation Date:** 2024-08-11

This document provides a comprehensive overview of the QnA Evaluator application's architecture, data flow, and key components. It is intended for developers working on the project to understand its structure and how to introduce changes.

---

## 1. Core Philosophy

The application is designed as a **Single Page Application (SPA)** with a declarative UI built in **React**. It operates on a set of questions defined in a static JSON file and uses a backend service (implemented in both Node.js and Python) to interact with the OpenAI API for scoring answers and generating reports.

The key principles are:
- **Declarative UI**: The entire questionnaire, including questions, dependencies, and input types, is defined in a single JSON file (`q4.json`). The UI dynamically renders itself based on this configuration.
- **Centralized State Management**: React's Context API (`AppContext`) holds all critical application state (answers, scores, question states), providing a single source of truth and simplifying data flow between components.
- **Stateless Backend**: The API endpoints are stateless. They receive all necessary data in the request body, perform an action (call OpenAI), and return a result without storing any session information.

---

## 2. Component Versions

- **React:** 18.2.0
- **Node.js (for Vercel runtime):** 18.x
- **OpenAI Node.js Library:** 5.12.2
- **Python:** 3.x (as per local environment)
- **Flask:** (as per `requirements.txt`)
- **OpenAI Python Library:** (as per `requirements.txt`)

---

## 3. Frontend Architecture (`src/`)

The frontend is responsible for rendering the user interface, managing user input, and orchestrating API calls to the backend.

### 3.1. Data Loading and State Management

1.  **Entry Point (`App.js`):** This is the root component. It initializes the `AppContext`, which will be used by all child components to access and modify global state.
2.  **Data Source (`public/questions/q4.json`):** This JSON file is the single source of truth for the entire questionnaire. It contains:
    *   `questions`: A flat list of all questions, each with a unique `id`, `text`, `question_type`, UI hints, and AI context.
    *   `meta_questions`: A subset of questions for basic information.
    *   `final_analysis_config`: A declarative structure defining how the final report should be generated, including prompts, models, and context for each section.
    *   `calculations`: Rules for calculating derived scores (e.g., `OVERALL`).
3.  **Loading (`useLoadQuestions.js`):** This custom hook is called by `App.js`. It fetches `/questions/q4.json` and processes the data, grouping questions into sections based on their `cluster_name`.
4.  **State Initialization & Persistence (`App.js`):** On startup, `App.js` attempts to load `answers`, `scores`, and `questionStates` from the browser's `localStorage`. It then uses `useEffect` hooks to automatically save any changes to this state back to `localStorage`, preserving user progress.

### 3.2. Rendering Logic: From JSON to GUI

1.  **`QuestionSection.js`:** This is the main container for the questionnaire. It receives the processed `sections` from `AppContext`.
2.  **Iteration:** It maps over the `sections` array and, for each question within a section, it renders an `<AnswerInput />` component.
3.  **`AnswerInput.js`:** This is a versatile component that renders the appropriate HTML input field based on the `question_type` from the question object (e.g., `text`, `yes-no`, `choice-single`). It reads the `ui` property to decide whether to render radio buttons or a dropdown. It also handles rendering conditional follow-up questions.
4.  **State Updates:** When a user interacts with an input, `AnswerInput.js` calls the `onAnswer` function passed down from `QuestionSection.js`. This function updates the global `answers` object in `AppContext`, triggering a re-render.

### 3.3. Dependency Management and State Machine

A crucial feature is the question dependency system, which controls when a question can be evaluated by the AI.

-   **`getQuestionState` (`QuestionSection.js`):** This function determines the state of a question (`unanswered`, `partially_answered`, `fully_answered`).
    *   An answer is **`fully_answered`** if it has a value and either requires no AI score (`"score": "NO"`) or has received a score from the AI.
    -   An answer is **`partially_answered`** if it has a value but is still awaiting an AI score (and its dependencies are met).
-   **`cascadeUpdateDependents` (`QuestionSection.js`):** When a question becomes `fully_answered`, this function is triggered. It finds all other questions that depend on the newly answered one and re-evaluates their state, potentially triggering new AI evaluations.

---

## 4. Backend Architecture (`src/backend/`)

The backend consists of a set of serverless functions responsible for securely interacting with the OpenAI API. There are two parallel implementations: Node.js/JavaScript (`.mjs`) and Python (`.py`).

### 4.1. Node.js Implementation (for Vercel)

-   **Location:** `src/backend/*.mjs`
-   **Server:** `local-api-server.mjs` (for local development), but primarily designed for the Vercel serverless environment.
-   **Key Files:**
    -   `simple-evaluate.mjs`: Handles scoring for a single question.
    -   `final-analysis.mjs`: Handles generation of the final report sections.

### 4.2. Python Implementation

-   **Location:** `src/backend/*.py`
-   **Server:** `py_local_api_server.py` (a Flask-based server for local development).
-   **Key Files:**
    -   `py_simple_evaluate.py`: Contains the business logic for scoring a single question.
    -   `py_final_analysis.py`: Contains the business logic for generating the final report.

### 4.3. Backend-AI Interaction

1.  **Prompt Location:** The main system prompt is located at `public/questions/ai-prompt.txt`. Specific prompt additions and configurations are inside `q4.json`.
2.  **Request from Frontend:** The frontend sends a POST request to a backend endpoint.
3.  **Prompt Construction:** The backend logic (`simple-evaluate` or `final-analysis`) receives the request. It loads the base prompt from `ai-prompt.txt` and the relevant configuration from `q4.json`. It constructs a detailed prompt by combining the base prompt, the user's answer, and any necessary context from other answers as defined in the `ai_context` of the question.
4.  **API Call:** The backend sends the fully constructed prompt to the OpenAI API (`chat.completions.create`). **Crucially, the API Key and Project ID are stored as environment variables on the server and are never exposed to the frontend.**
5.  **Retry Logic:** Both backend implementations include a robust retry mechanism with exponential backoff and jitter to handle OpenAI API Rate Limit errors (HTTP 429) gracefully.

---

## 5. Frontend-Backend Communication

Communication happens via HTTP POST requests from the React frontend to the backend API endpoints.

### `/api/simple-evaluate.mjs`

-   **Direction:** Frontend -> Backend
-   **Purpose:** To get an AI score for a single question.
-   **Request Body (JSON):**
    ```json
    {
      "questionId": "SG01",
      "allAnswers": { "MET.LOC": "us", "SG01": "Some user answer" }
    }
    ```
-   **Response Body (JSON):**
    ```json
    {
      "score": 85,
      "explanation": "The answer is comprehensive and addresses all parts of the question."
    }
    ```

### `/api/final-analysis.mjs`

-   **Direction:** Frontend -> Backend
-   **Purpose:** To generate one section of the final analysis report.
-   **Request Body (JSON):**
    ```json
    {
      "section_index": 0,
      "answers": { "...": "..." },
      "scores": { "...": 0 },
      "final_analysis_config": { ... } // The config block from q4.json
    }
    ```
-   **Response Body (JSON):**
    ```json
    {
      "report": "This is the generated text for the report section..."
    }
    ```

---

## 6. Maintainability

-   **To add/modify questions:** Edit `public/questions/q4.json`. The UI will update automatically. No frontend code changes are needed for simple additions.
-   **To change scoring logic:** Modify the prompts in `q4.json` or `ai-prompt.txt`. For more complex changes, edit the prompt construction logic in `src/backend/simple-evaluate.mjs` or its Python equivalent.
-   **To change UI components:** Edit the relevant React components in `src/`. For example, to change how dropdowns look, modify `src/AnswerInput.js`.

---

## 7. Notes (Special Cases)

-   **Duplicated Logic:** The score calculation logic in `applyCalculations` is duplicated in `QuestionSection.js` and `SidebarResults.js`. A change in one must be mirrored in the other. This should be refactored into a shared utility function.
-   **Scoreless Questions:** Questions with `"score": "NO"` in `q4.json` are considered `fully_answered` as soon as a value is provided, bypassing the AI evaluation call.
-   **Hidden Questions:** Questions with `"ui_hidden": true` are loaded into the state but not rendered in the UI. They can be used to provide context to the AI without user interaction.

---

## 8. Build, Install, Run

### Installation
1.  Clone the repository.
2.  Install dependencies: `npm install`
3.  (For Python backend) Install Python dependencies: `pip install -r src/backend/requirements.txt`

### Running the Application

1.  **Create `.env` file:** In the root directory, create a file named `.env` and add your OpenAI credentials:
    ```
    REACT_APP_GPT_KEY=sk-your-openai-api-key
    REACT_APP_PROJECT_ID=proj_your-openai-project-id
    ```
2.  **Start Frontend and Node.js Backend:**
    ```bash
    npm run start:local
    ```
    This will start the React development server on `http://localhost:3000` and the Node.js local API server on `http://localhost:3001`.
3.  **Start Frontend and Python Backend:**
    -   In one terminal, start the React server: `npm start`
    -   In a second terminal, start the Python server: `python src/backend/py_local_api_server.py`

### Building for Production
```bash
npm run build
```
This creates a production-ready build in the `build/` directory. For deployment, Vercel is configured via `vercel.json` to use this directory and the serverless functions in `src/backend/`.

---

## 9. Integration

The application is designed for easy integration. The core logic is decoupled from the UI. The question set can be replaced by pointing `useLoadQuestions.js` to a different JSON file. The backend can be swapped between Node.js and Python by changing the proxy target in `package.json` or the Vercel rewrite rules.

---

## 10. TODO

-   [ ] Refactor `applyCalculations` into a shared utility function to remove code duplication.
-   [ ] Improve the `format_data_for_prompt` function in `py_final_analysis.py` to achieve full parity with the Node.js version, including looking up question text by ID.
-   [ ] Add comprehensive unit and integration tests for both frontend and backend logic.

## 11. FIX

-   [ ] The red border highlighting for unanswered questions does not always work correctly for text input fields, remaining red even after an answer is provided. This is due to the timing of state updates and re-renders.
-   [ ] The "Save to file" functionality may not work reliably on all browsers or without HTTPS, which is a browser security feature.
