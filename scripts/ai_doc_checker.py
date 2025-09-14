#!/usr/bin/env python3
"""
Complete AI Documentation Checker - Google Gemini Version
Detects FastAPI changes using git diff + regex and generates documentation
"""

import os
import re
import subprocess
import smtplib
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import sys
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class APIChange:
    method: str           # 'GET', 'POST', 'PUT', 'DELETE'
    path: str            # '/api/customers/{id}/preferences'
    function_name: str   # 'create_customer_preferences'
    file_path: str       # 'services/customer-service/main.py'
    code_snippet: str    # The function code
    line_number: int     # Line in file
    change_type: str     # 'new', 'modified', 'deleted'

@dataclass
class DocumentationUpdate:
    section_type: str    # 'api_reference', 'changelog'
    content: str         # Generated markdown
    location_hint: str   # Where to add in GitBook
    priority: str        # 'high', 'medium', 'low'

class FastAPIChangeDetector:
    """Detects FastAPI endpoint changes using git diff + regex"""
    
    FASTAPI_PATTERNS = [
        r'@app\.(get|post|put|delete|patch)\s*\(',
        r'@router\.(get|post|put|delete|patch)\s*\(',
    ]
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
    
    def get_changed_python_files(self) -> List[str]:
        """Get Python files that changed in last commit"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD^', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("No git changes found or not in git repository")
                return []
            
            # Filter only Python files, exclude tests
            python_files = [
                f for f in result.stdout.strip().split('\n') 
                if f.endswith('.py') and 'test' not in f.lower() and f
            ]
            
            print(f"Changed Python files: {python_files}")
            return python_files
            
        except Exception as e:
            print(f"Error getting changed files: {e}")
            return []
    
    def get_file_diff(self, file_path: str) -> str:
        """Get git diff for specific file"""
        try:
            result = subprocess.run(
                ['git', 'diff', 'HEAD^', 'HEAD', '--', file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            print(f"Error getting diff for {file_path}: {e}")
            return ""
    
    def detect_api_changes(self, diff_content: str, file_path: str) -> List[APIChange]:
        """Extract API changes from diff content"""
        changes = []
        lines = diff_content.split('\n')
        
        for i, line in enumerate(lines):
            # Look for added lines with FastAPI decorators
            if not line.startswith('+'):
                continue
            
            # Remove the + prefix
            clean_line = line[1:].strip()
            
            # Check for FastAPI patterns
            for pattern in self.FASTAPI_PATTERNS:
                match = re.search(pattern, clean_line, re.IGNORECASE)
                if match:
                    method = match.group(1).upper()
                    
                    # Extract path from decorator
                    path_match = re.search(r'["\']([^"\']+)["\']', clean_line)
                    path = path_match.group(1) if path_match else 'unknown'
                    
                    # Find the function definition
                    function_info = self._find_function_definition(lines, i, file_path)
                    if function_info:
                        change = APIChange(
                            method=method,
                            path=path,
                            function_name=function_info['name'],
                            file_path=file_path,
                            code_snippet=function_info['code'],
                            line_number=function_info['line'],
                            change_type='new'
                        )
                        changes.append(change)
                        print(f"Detected new API: {method} {path}")
                    break
        
        return changes
    
    def _find_function_definition(self, lines: List[str], decorator_index: int, file_path: str) -> Optional[Dict]:
        """Find function definition after decorator"""
        
        # Look for function definition in next few lines
        for i in range(decorator_index + 1, min(decorator_index + 10, len(lines))):
            line = lines[i]
            clean_line = line.lstrip('+- ').strip()
            
            # Skip other decorators and empty lines
            if not clean_line or clean_line.startswith('@'):
                continue
            
            # Found function definition
            func_match = re.search(r'(?:async\s+)?def\s+(\w+)', clean_line)
            if func_match:
                function_name = func_match.group(1)
                
                # Get full function code from current file
                full_code = self._get_full_function_code(file_path, function_name)
                
                return {
                    'name': function_name,
                    'code': full_code,
                    'line': i + 1
                }
        
        return None
    
    def _get_full_function_code(self, file_path: str, function_name: str) -> str:
        """Get complete function code from current file"""
        try:
            with open(os.path.join(self.repo_path, file_path), 'r') as f:
                content = f.read()
            
            # Simple approach: find function and get ~15 lines
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if f'def {function_name}(' in line:
                    # Get function + docstring + some body
                    end_line = min(i + 20, len(lines))
                    function_lines = lines[i:end_line]
                    
                    # Stop at next function/class definition
                    for j, func_line in enumerate(function_lines[1:], 1):
                        if (func_line.strip().startswith('def ') or 
                            func_line.strip().startswith('class ') or
                            func_line.strip().startswith('@app.') or
                            func_line.strip().startswith('@router.')):
                            function_lines = function_lines[:j]
                            break
                    
                    return '\n'.join(function_lines)
            
            return f"# Function {function_name} not found in current file"
            
        except Exception as e:
            return f"# Error reading function: {e}"

class GeminiDocumentationGenerator:
    """Generates documentation using Google Gemini"""
    
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')  # Using flash for speed and cost
    
    def generate_api_documentation(self, api_change: APIChange) -> str:
        """Generate API documentation using Google Gemini"""
        
        service_name = self._extract_service_name(api_change.file_path)
        
        prompt = f"""
Generate complete API documentation for this FastAPI endpoint:

**Endpoint:** {api_change.method} {api_change.path}
**Function:** {api_change.function_name}
**Service:** {service_name}
**File:** {api_change.file_path}

**Code:**
```python
{api_change.code_snippet}
```

Generate documentation in this EXACT format:

## {api_change.method} {api_change.path}

**Description:** [Brief 1-2 sentence description of what this endpoint does]

**Parameters:**
- `parameter_name` (type): Description of parameter

**Request Example:**
```json
{{
  "example": "request_data"
}}
```

**Response Example:**
```json
{{
  "example": "response_data"  
}}
```

**Error Responses:**
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors

**Notes:**
- Any important implementation details
- Related endpoints or functionality

Make it professional, concise, and developer-friendly. Base the content on the actual code provided.
"""
        
        try:
            # Generate content with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.3,
                            max_output_tokens=800,
                        )
                    )
                    
                    if response.text:
                        return response.text.strip()
                    else:
                        print(f"Empty response from Gemini on attempt {attempt + 1}")
                        
                except Exception as e:
                    print(f"Gemini API error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            
            # If all attempts fail, return fallback
            print("All Gemini API attempts failed, using fallback documentation")
            return self._generate_fallback_docs(api_change)
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return self._generate_fallback_docs(api_change)
    
    def generate_changelog_entry(self, api_change: APIChange) -> str:
        """Generate changelog entry using Google Gemini"""
        
        service_name = self._extract_service_name(api_change.file_path)
        today = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""
Generate a changelog entry for this new API endpoint:

**Date:** {today}
**Endpoint:** {api_change.method} {api_change.path}
**Service:** {service_name}
**Function:** {api_change.function_name}

**Code Context:**
```python
{api_change.code_snippet[:300]}...
```

Format as:

### {today}

#### 🚀 New Features
- **{service_name.title()} Service**: Added `{api_change.method} {api_change.path}` endpoint
  - [Brief description of what it does]
  - [Who would use this and why]

#### 📝 Technical Details
- New endpoint: `{api_change.method} {api_change.path}`
- Function: `{api_change.function_name}`
- Service: {service_name}

Keep it concise and user-focused.
"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=300,
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                return self._generate_fallback_changelog(api_change)
            
        except Exception as e:
            print(f"Error generating changelog with Gemini: {e}")
            return self._generate_fallback_changelog(api_change)
    
    def _extract_service_name(self, file_path: str) -> str:
        """Extract service name from file path"""
        parts = file_path.split('/')
        if 'services' in parts:
            idx = parts.index('services')
            if idx + 1 < len(parts):
                service = parts[idx + 1]
                return service.replace('-service', '').replace('_service', '')
        return 'api'
    
    def _generate_fallback_docs(self, api_change: APIChange) -> str:
        """Fallback documentation if Gemini fails"""
        return f"""
## {api_change.method} {api_change.path}

**Description:** {api_change.function_name.replace('_', ' ').title()}

**Function:** `{api_change.function_name}`

**Request/Response:** See code implementation for details.

**Notes:** This endpoint was automatically detected. Please review and update documentation as needed.
"""
    
    def _generate_fallback_changelog(self, api_change: APIChange) -> str:
        """Fallback changelog if Gemini fails"""
        today = datetime.now().strftime('%Y-%m-%d')
        return f"""
### {today}

#### 🚀 New Features
- Added `{api_change.method} {api_change.path}` endpoint
- Function: `{api_change.function_name}`
"""

class GmailNotifier:
    """Sends notifications via Gmail"""
    
    def __init__(self, gmail_user: str, gmail_password: str):
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
    
    def send_documentation_notification(self, api_changes: List[APIChange], 
                                       api_docs: List[str], changelog_docs: List[str],
                                       recipient: str):
        """Send Gmail notification with generated documentation"""
        
        if not api_changes:
            print("No API changes to notify about")
            return
        
        subject = f"📝 API Documentation Update Required - {len(api_changes)} new endpoint(s)"
        
        # Create email content
        email_content = self._create_email_content(api_changes, api_docs, changelog_docs)
        
        # Send email
        try:
            msg = MIMEMultipart()
            msg['From'] = self.gmail_user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(email_content, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.gmail_user, self.gmail_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Documentation notification sent to {recipient}")
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
    
    def _create_email_content(self, api_changes: List[APIChange], 
                            api_docs: List[str], changelog_docs: List[str]) -> str:
        """Create the email notification content"""
        
        content = f"""
📝 API DOCUMENTATION UPDATE REQUIRED

Hi Team,

{len(api_changes)} new API endpoint(s) detected and documentation has been generated automatically using Google Gemini.

DETECTED CHANGES:
"""
        
        for i, change in enumerate(api_changes):
            content += f"""
{i+1}. {change.method} {change.path}
   Function: {change.function_name}
   File: {change.file_path}
"""
        
        content += "\n" + "="*70 + "\n"
        content += "GENERATED DOCUMENTATION (Powered by Google Gemini):\n"
        content += "="*70 + "\n\n"
        
        # API Reference Updates
        for i, (change, docs) in enumerate(zip(api_changes, api_docs)):
            content += f"""
📋 UPDATE #{i+1}: API REFERENCE DOCUMENTATION

WHERE TO ADD: Go to GitBook → API Reference → Customer Service
ACTION: Copy the markdown below and add to the page

CONTENT TO ADD:
----------------------------------------
{docs}
----------------------------------------

"""
        
        # Changelog Updates
        content += f"""
📋 CHANGELOG UPDATE

WHERE TO ADD: Go to GitBook → Changelog page
ACTION: Add to the TOP of the changelog (most recent first)

CONTENT TO ADD:
----------------------------------------
"""
        
        for changelog_doc in changelog_docs:
            content += f"{changelog_doc}\n\n"
        
        content += "----------------------------------------\n\n"
        
        content += f"""
QUICK LINKS:
- API Reference: https://your-company.gitbook.io/docs/api-reference
- Changelog: https://your-company.gitbook.io/docs/changelog

NEXT STEPS:
1. Review the generated documentation above
2. Copy-paste the sections into GitBook
3. Make any necessary edits for accuracy
4. Reply to this email when complete

Generated by AI Documentation Assistant (Google Gemini)
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return content

def main():
    """Main execution function"""
    
    print("🚀 Starting AI Documentation Checker (Google Gemini)...")
    
    # Load environment variables
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    gmail_user = os.getenv('GMAIL_USER')
    gmail_password = os.getenv('GMAIL_PASSWORD')
    notification_email = os.getenv('NOTIFICATION_EMAIL')
    
    # Validate environment
    missing_vars = []
    if not gemini_api_key:
        missing_vars.append('GEMINI_API_KEY')
    if not gmail_user:
        missing_vars.append('GMAIL_USER')
    if not gmail_password:
        missing_vars.append('GMAIL_PASSWORD')
    if not notification_email:
        missing_vars.append('NOTIFICATION_EMAIL')
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or GitHub secrets")
        return 1
    
    # Initialize components
    detector = FastAPIChangeDetector()
    generator = GeminiDocumentationGenerator(gemini_api_key)
    notifier = GmailNotifier(gmail_user, gmail_password)
    
    # Step 1: Detect changes
    print("🔍 Detecting changed Python files...")
    changed_files = detector.get_changed_python_files()
    
    if not changed_files:
        print("✅ No Python files changed - no documentation updates needed")
        return 0
    
    # Step 2: Analyze each changed file
    all_api_changes = []
    
    for file_path in changed_files:
        print(f"📄 Analyzing {file_path}...")
        diff_content = detector.get_file_diff(file_path)
        
        if diff_content:
            api_changes = detector.detect_api_changes(diff_content, file_path)
            all_api_changes.extend(api_changes)
    
    if not all_api_changes:
        print("✅ No FastAPI endpoints changed - no documentation updates needed")
        return 0
    
    print(f"🎯 Found {len(all_api_changes)} API changes")
    
    # Step 3: Generate documentation
    print("🤖 Generating documentation with Google Gemini...")
    
    api_docs = []
    changelog_docs = []
    
    for change in all_api_changes:
        print(f"  Generating docs for {change.method} {change.path}...")
        
        # Generate API documentation
        api_doc = generator.generate_api_documentation(change)
        api_docs.append(api_doc)
        
        # Generate changelog entry
        changelog_doc = generator.generate_changelog_entry(change)
        changelog_docs.append(changelog_doc)
    
    # Step 4: Send notification
    print("📧 Sending email notification...")
    notifier.send_documentation_notification(
        all_api_changes, api_docs, changelog_docs, notification_email
    )
    
    print("✅ AI Documentation Checker completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())