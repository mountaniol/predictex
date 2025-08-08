# Vercel Deployment

## Prerequisites

1. Install [Vercel CLI](https://vercel.com/docs/cli):
```bash
npm i -g vercel
```

2. Make sure you have an account on [Vercel](https://vercel.com)

## Deployment Steps

### 1. Project Preparation

Make sure all files are ready:
- ✅ `vercel.json` - Vercel configuration
- ✅ `api/evaluate.js` - serverless API function
- ✅ `package.json` - updated for Vercel
- ✅ `.vercelignore` - file exclusions

### 2. Environment Variables Setup

Add environment variable in Vercel Dashboard or via CLI:

```bash
vercel env add OPENAI_API_KEY
```

Or in Vercel Dashboard:
1. Go to Settings → Environment Variables
2. Add `OPENAI_API_KEY` with your OpenAI key

### 3. Deployment

#### Option A: Via Vercel CLI
```bash
# In qna-evaluator directory
vercel

# Follow the instructions:
# - Select project or create new one
# - Confirm settings
# - Wait for deployment completion
```

#### Option B: Via GitHub
1. Upload code to GitHub repository
2. Connect repository to Vercel
3. Configure environment variables
4. Deploy project

### 4. Deployment Verification

After deployment, check:

1. **Frontend**: `https://your-project.vercel.app`
2. **API**: `https://your-project.vercel.app/api/evaluate`

### 5. API Testing

```bash
curl -X POST https://your-project.vercel.app/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "system": "You are an expert business evaluator.",
    "question": {"id": "TEST", "text": "Test question"},
    "answer": {"value": "Test answer"}
  }'
```

## Project Structure for Vercel

```
qna-evaluator/
├── api/
│   └── evaluate.js          # Serverless API function
├── public/
│   ├── q3.json             # Question data
│   └── ai-prompt.txt       # AI prompt
├── src/                    # React components
├── vercel.json            # Vercel configuration
├── package.json           # Dependencies and scripts
└── .vercelignore          # File exclusions
```

## Troubleshooting

### 1. Error "OpenAI API key not configured"
- Make sure `OPENAI_API_KEY` environment variable is set in Vercel
- Verify the key is valid

### 2. CORS Error
- API function is already configured for CORS
- Make sure requests go to the correct endpoint

### 3. Build Error
- Check that all dependencies are installed
- Make sure `package.json` is correct

### 4. Files Not Loading
- Check that files are in the `public/` folder
- Make sure paths in code are correct

## Deployment Updates

To update:
```bash
vercel --prod
```

Or when pushing to GitHub (if auto-deploy is configured).

## Monitoring

In Vercel Dashboard you can:
- View function logs
- Monitor performance
- Configure domains
- Manage environment variables
