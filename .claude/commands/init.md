Run the fred-mAIyer initialization wizard by executing:

```
uv run fred-maiyer init
```

This is an interactive CLI wizard. It will prompt the user in the terminal for input at each step. Your job is to run the command and help the user if they get stuck.

**Before running**, briefly explain what the wizard will do:
1. Ask for Kroger API credentials (from https://developer.kroger.com)
2. Open a browser to connect their Fred Meyer / Kroger account via OAuth2
3. Let them pick their local Fred Meyer store by ZIP code
4. Optionally connect a Google Tasks list as a shopping list source
5. Save everything to a local `.env` file (never committed to git)

**If the user hasn't registered a Kroger developer app yet**, walk them through it:
- Go to https://developer.kroger.com and create an account
- Create a new application
- Set the redirect URI to `http://localhost:8888/callback`
- Copy the Client ID and Client Secret

**If the user wants to use Google Tasks as a shopping list**, they'll need:
- A Google Cloud project with the Tasks API enabled
- OAuth2 credentials from https://console.cloud.google.com/apis/credentials
- The redirect URI `http://localhost:8889/callback` added to authorized redirect URIs
- This step is optional — they can skip it by answering "N"

**If the wizard fails**, read the error message and help troubleshoot. Common issues:
- Invalid credentials → double-check Client ID / Secret at developer.kroger.com
- Port 8888 in use → the wizard will fall back to manual code paste
- Port 8889 in use → Google Tasks OAuth will fall back to manual code paste
- Token exchange fails → ensure the redirect URI in the Kroger app matches exactly
- Google Tasks auth fails → ensure Tasks API is enabled in the Google Cloud Console
