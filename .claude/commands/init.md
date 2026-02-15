Run the fred-mAIyer initialization wizard by executing:

```
uv run fred-maiyer init
```

This is an interactive CLI wizard. It will prompt the user in the terminal for input at each step. Your job is to run the command and help the user if they get stuck.

**Before running**, briefly explain what the wizard will do:
1. Ask for Kroger API credentials (from https://developer.kroger.com)
2. Open a browser to connect their Fred Meyer / Kroger account via OAuth2
3. Let them pick their local Fred Meyer store by ZIP code
4. Save everything to a local `.env` file (never committed to git)

**If the user hasn't registered a Kroger developer app yet**, walk them through it:
- Go to https://developer.kroger.com and create an account
- Create a new application
- Set the redirect URI to `http://localhost:8888/callback`
- Copy the Client ID and Client Secret

**If the wizard fails**, read the error message and help troubleshoot. Common issues:
- Invalid credentials → double-check Client ID / Secret at developer.kroger.com
- Port 8888 in use → the wizard will fall back to manual code paste
- Token exchange fails → ensure the redirect URI in the Kroger app matches exactly
