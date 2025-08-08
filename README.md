# QnA Evaluator

Intelligent business risk assessment system based on questions and answers using AI.

## 🚀 Quick Start

### Local Development

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd qna-evaluator
```

2. **Install dependencies:**
```bash
npm install
```

3. **Set up environment variables:**
```bash
# Create .env file in the project root
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

4. **Start the project:**
```bash
# Start frontend only (for development)
npm start

# Or use script to start frontend + backend
./start-dev.sh
```

### Deploy to Vercel

To deploy to [Vercel](https://vercel.com):

1. **Install Vercel CLI:**
```bash
npm i -g vercel
```

2. **Deploy the project:**
```bash
vercel
```

3. **Configure environment variables in Vercel Dashboard:**
   - `OPENAI_API_KEY` - your OpenAI API key

Detailed instructions: [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)

## 📁 Project Architecture

```
qna-evaluator/
├── src/                    # React components
│   ├── App.js             # Main component with AppContext
│   ├── QuestionSection.js # Question display
│   ├── MetaQuestionsSection.js # Meta questions
│   ├── AnswerInput.js     # Universal input component
│   ├── LanguageSelector.js # Language selection
│   ├── Header.js          # Header
│   ├── Footer.js          # Footer
│   └── useLoadQuestions.js # Data loading hook
├── public/                # Static files
│   ├── q3.json           # New question format
│   ├── questions2.json   # Legacy format
│   └── ai-prompt.txt     # AI prompt
├── api/                  # Vercel serverless functions
│   └── evaluate.js       # API for answer evaluation
├── backend/              # Local Express server
│   ├── server.js         # Main server
│   └── package.json      # Backend dependencies
├── vercel.json          # Vercel configuration
├── package.json         # Frontend dependencies
└── start-dev.sh         # Startup script
```

## 🎯 Features

### Supported Question Types:
- **choice-single** - single selection (radio/dropdown)
- **choice-multi** - multiple selection with constraints
- **yes-no** - yes/no questions
- **text** - single-line input
- **textarea** - multi-line input
- **number** - numeric input
- **internal** - hidden questions

### Additional Capabilities:
- ✅ **Follow-up questions** - appear when selecting specific options
- ✅ **Hint and Info** - hints and additional information
- ✅ **"Other" options** - with additional text field
- ✅ **Maximum selections** for multi-select
- ✅ **Ranked selection** for multi-select
- ✅ **Dependency system** between questions
- ✅ **Multi-language support** (English, Russian, German)
- ✅ **AI evaluation** of answers with context

### Data Formats:
- **q3.json** - new format with meta-questions and extended functionality
- **questions2.json** - legacy format for backward compatibility

## 🔧 Technologies

### Frontend:
- **React 18** - UI library
- **React Context API** - state management
- **React Hooks** - functional components
- **CSS-in-JS** - styling

### Backend:
- **Vercel Functions** - serverless API (production)
- **Express.js** - local server (development)
- **OpenAI API** - AI answer evaluation
- **Axios** - HTTP client

### Infrastructure:
- **Vercel** - hosting and deployment
- **GitHub** - version control
- **npm** - dependency management

## 📊 API

### Endpoint: `/api/evaluate`

**Request:**
```json
{
  "system": "AI system prompt",
  "prompt_add": "Question-specific scoring rules",
  "meta": {
    "MET.LOC": "location",
    "MET.IND": "industry"
  },
  "question": {
    "id": "SG01",
    "text": "Question text"
  },
  "answer": {
    "value": "selected option or text",
    "extra": {
      "follow_up_id": "follow-up answer"
    },
    "other_text": "other option text"
  },
  "answers_ctx": {
    "SG01": "previous answer"
  }
}
```

**Response:**
```json
{
  "score": 85
}
```

## 🌐 Deployment

### Vercel (recommended)
- Automatic deployment from Git
- Serverless functions
- CDN for static files
- SSL certificates
- Monitoring and logs

### Local Server
- Express.js server
- For development and testing
- Requires CORS configuration

## 🔒 Security

- API keys stored in environment variables
- CORS configured for security
- Input data validation
- API error handling

## 📝 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Create a Pull Request

## 📞 Support

If you encounter issues:
1. Check [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md)
2. Ensure all dependencies are installed
3. Verify environment variables
4. Create an Issue in the repository


