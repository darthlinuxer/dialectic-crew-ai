---
name: update-cursor-settings
description: Modify editor/IDE user settings in settings.json. Use when the user
  wants to change editor settings, preferences, configuration, themes, font size,
  tab size, format on save, auto save, keybindings, or any settings.json values.
---

# Updating Editor Settings

This skill guides you through modifying editor/IDE user settings. Use this when the user wants to change editor settings, preferences, configuration, themes, keybindings, or any `settings.json` values. Settings file location is IDE-specific; check your platform's documentation for the correct path.

## Settings File Location (IDE-specific)

Paths vary by IDE. For Claude Code and other editors, see your platform's docs. Common patterns:
| OS | Example path (VSCode-based) |
|----|------|
| macOS | ~/Library/Application Support/[IDE]/User/settings.json |
| Linux | ~/.config/[IDE]/User/settings.json |
| Windows | %APPDATA%\[IDE]\User\settings.json |

## Before Modifying Settings

1. **Read the existing settings file** to understand current configuration
2. **Preserve existing settings** - only add/modify what the user requested
3. **Validate JSON syntax** before writing to avoid breaking the editor

## Modifying Settings

### Step 1: Read Current Settings

```typescript
// Read the settings file first
const settingsPath = "<your-IDE-user-settings-path>";
// Use the Read tool to get current contents
```

### Step 2: Identify the Setting to Change

Common setting categories:
- **Editor**: `editor.fontSize`, `editor.tabSize`, `editor.wordWrap`, `editor.formatOnSave`
- **Workbench**: `workbench.colorTheme`, `workbench.iconTheme`, `workbench.sideBar.location`
- **Files**: `files.autoSave`, `files.exclude`, `files.associations`
- **Terminal**: `terminal.integrated.fontSize`, `terminal.integrated.shell.*`
- **IDE-specific**: Settings prefixed with your IDE's namespace (e.g. `cursor.`, `aipopup.`)

### Step 3: Update the Setting

When modifying settings.json:
1. Parse the existing JSON (handle comments - VSCode settings support JSON with comments)
2. Add or update the requested setting
3. Preserve all other existing settings
4. Write back with proper formatting (2-space indentation)

### Example: Changing Font Size

If user says "make the font bigger":

```json
{
  "editor.fontSize": 16
}
```

### Example: Enabling Format on Save

If user says "format my code when I save":

```json
{
  "editor.formatOnSave": true
}
```

### Example: Changing Theme

If user says "use dark theme" or "change my theme":

```json
{
  "workbench.colorTheme": "Default Dark Modern"
}
```

## Important Notes

1. **JSON with Comments**: Many editors' settings.json supports comments (`//` and `/* */`). When reading, be aware comments may exist. When writing, preserve comments if possible.

2. **Restart May Be Required**: Some settings take effect immediately, others require reloading the window or restarting the editor. Inform the user if a restart is needed.

3. **Backup**: For significant changes, consider mentioning the user can undo via Ctrl/Cmd+Z in the settings file or by reverting git changes if tracked.

4. **Workspace vs User Settings**:
   - User settings (what this skill covers): Apply globally to all projects
   - Workspace settings (`.vscode/settings.json`): Apply only to the current project

## Common User Requests → Settings

| User Request | Setting |
|--------------|---------|
| "bigger/smaller font" | `editor.fontSize` |
| "change tab size" | `editor.tabSize` |
| "format on save" | `editor.formatOnSave` |
| "word wrap" | `editor.wordWrap` |
| "change theme" | `workbench.colorTheme` |
| "hide minimap" | `editor.minimap.enabled` |
| "auto save" | `files.autoSave` |
| "line numbers" | `editor.lineNumbers` |
| "bracket matching" | `editor.bracketPairColorization.enabled` |
| "cursor style" | `editor.cursorStyle` |
| "smooth scrolling" | `editor.smoothScrolling` |

## Workflow

1. Read the user's IDE settings file (path is IDE-specific)
2. Parse the JSON content
3. Add/modify the requested setting(s)
4. Write the updated JSON back to the file
5. Inform the user the setting has been changed and whether a reload is needed
