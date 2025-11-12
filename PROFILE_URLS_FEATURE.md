# Profile URLs Feature

## Overview
Added support for LinkedIn, GitHub, and LeetCode profile URLs in the resume optimization system. These URLs are:
- Collected from the frontend form
- Stored in the database
- Passed to the LLM for inclusion in optimized resumes
- Embedded as clickable links in the generated PDF

## Changes Made

### 1. Database (Backend/models.py)
Added three new optional columns to the `resumes` table:
- `linkedin_url`
- `github_url`
- `leetcode_url`

### 2. API Schema (Backend/schemas.py)
Updated Pydantic models to include the new URL fields as optional strings.

### 3. Backend API (Backend/routers/Resume_getter.py)
- Added three new optional form parameters to `/optimize_resume` endpoint
- URLs are passed to the agent graph in the state
- Database save code updated (commented out section)

### 4. Agent State (Agent/graph/graph_setup.py)
Added URL fields to `AgentState` TypedDict so they're available throughout the agent workflow.

### 5. LLM System Prompt (Agent/llm/llm_setup.py)
- System prompt now includes profile URLs when provided
- Instructs the LLM to include these URLs in the contact section
- Emphasizes the importance of including the URLs

### 6. PDF Generation (Agent/tools/pdf_tools.py)
- Updated `process_text_formatting()` to convert URLs to clickable links
- URLs are automatically detected and wrapped in `<link>` tags
- Contact section now supports clickable hyperlinks

### 7. Frontend Form (Frontend/src/components/InitialForm.tsx)
- Added three new input fields for profile URLs
- Fields are optional and styled in a dedicated section
- URLs are sent to the backend via FormData

### 8. Database Migration (Backend/migrations/add_profile_urls.py)
Created a migration script to add the new columns to existing databases.

## Usage

### For Users
1. Fill in the resume upload form as usual
2. Optionally add your LinkedIn, GitHub, and/or LeetCode URLs in the "Profile URLs" section
3. Submit the form
4. The optimized resume will include these URLs as clickable links in the contact section

### For Developers

#### Running the Migration
If you have an existing database, run the migration:
```bash
cd Backend
python migrations/add_profile_urls.py
```

#### Testing
1. Start the backend: `cd Backend && uvicorn main:app --reload`
2. Start the frontend: `cd Frontend && npm run dev`
3. Upload a resume with profile URLs
4. Verify the URLs appear in the generated PDF

## Technical Details

### URL Detection
The PDF generator automatically detects and converts URLs to clickable links using regex:
- Full URLs: `https://linkedin.com/in/username`
- Domain-relative: `linkedin.com/in/username`
- Common platforms: linkedin.com, github.com, leetcode.com

### LLM Integration
The system prompt explicitly instructs the LLM to:
1. Include provided URLs in the contact section
2. Format them appropriately
3. Ensure they're part of the `contact_line` parameter when calling `optimize_resume_sections`

### Database Storage
URLs are stored as nullable VARCHAR fields, allowing:
- Users to provide none, some, or all URLs
- Future expansion to additional profile platforms
- Easy querying and filtering by profile presence
