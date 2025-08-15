# Manual Testing Guide for Debounce Functionality

## Overview
The debounce functionality delays request sending by 1 second from the last user interaction. This prevents excessive API calls when users rapidly interact with form elements.

## Test Scenarios

### 1. Text Input Debouncing
**Steps:**
1. Navigate to any question with text input (e.g., company name, location)
2. Start typing rapidly
3. Observe console logs for debounce behavior

**Expected Behavior:**
- Console shows: `[handleAnswerChange] Canceling pending submission due to continued interaction`
- Only after 1 second of no typing should you see: `[QuestionSection] Debounced submission triggered for: [question_id]`
- API request (`POST /api/simple-evaluate.mjs`) should only be sent once

### 2. Checkbox/Radio Debouncing  
**Steps:**
1. Navigate to multiple choice questions
2. Rapidly select/deselect multiple options
3. Observe console logs and network tab

**Expected Behavior:**
- Each rapid interaction cancels previous debounced submissions
- Final selection triggers API call after 1-second delay
- Only one API request sent for the final state

### 3. Mixed Interaction Debouncing
**Steps:**
1. Select a checkbox option
2. Immediately start typing in "Other" text field
3. Continue typing for several characters
4. Stop typing and wait

**Expected Behavior:**
- All interactions reset the 1-second timer
- Only final state (checkbox + text) gets evaluated
- Single API request after 1-second delay from last keystroke

## Console Log Patterns

### Normal Debounce Flow:
```
[handleAnswerChange] Canceling pending submission due to continued interaction with: SG01
[handleAnswerChange] Canceling pending submission due to continued interaction with: SG01  
[handleAnswerChange] Scheduling debounced submission for: SG01
[QuestionSection] Debounced submission triggered for: SG01
```

### Network Requests:
- Should see only one `POST /api/simple-evaluate.mjs` request per question after debounce delay
- No rapid-fire requests during user interaction

## Configuration

The debounce delay is configurable in `public/app.config.json`:
```json
{
  "Frontend": {
    "request_send_delay": 1000
  }
}
```

## Browser Developer Tools Testing

1. **Console Tab**: Monitor debounce log messages
2. **Network Tab**: Verify only final requests are sent
3. **Performance Tab**: Confirm reduced API call frequency improves performance

## Expected Benefits

- **Reduced API Calls**: ~90% reduction in evaluation requests during rapid input
- **Better User Experience**: No UI lag from excessive requests  
- **Server Load Reduction**: Fewer unnecessary AI evaluation calls
- **Cost Optimization**: Reduced OpenAI API usage for partial inputs