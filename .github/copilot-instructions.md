Keep a record of useful commands, examples, and development notes in appropriate documentation files:

- For PowerShell commands and tasks: Add to docs/powershell_commands.md
- For data processing workflows: Add to docs/data_processing.md  
- For provider API usage: Add to docs/provider_guides.md
- For testing procedures: Add to docs/testing.md
- For daily development notes: Add to docs/daily_notes/{current_date}.md

When working with code:
1. If a command fails and then succeeds with correct syntax, document the working solution
2. Add clear descriptions and expected outputs where helpful
3. Organize entries with clear headings and categories
4. If a documentation file grows too large (>1000 lines), suggest splitting it into focused topics

When creating new projects:
- Check if templates are available for the framework being used
- Reference latest release documentation and quick start guides 
- Use documented generation methods rather than manual setup when available

Always consult existing documentation before creating duplicate examples.

When creating a new project, always check if there is a template available for the framework you are using.
When creating a new project based on a framework, look up the latest release documentation, quick start guide etc.
Where available based on the documentation retrieved, generate the project using the documented method / scripts rather than manually.